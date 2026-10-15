import csv
import io
import json
import re
import uuid
from typing import List, Dict, Any, Tuple, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.models.dataset import Dataset, DatasetVersion, EvaluationCase
from app.schemas.dataset import (
    EvaluationCaseCreate,
    DatasetUploadSummary,
    DatasetStatistics
)

class DatasetValidationError(Exception):
    def __init__(self, message: str, errors: Optional[List[str]] = None):
        super().__init__(message)
        self.errors = errors or [message]

class DatasetParser:
    @staticmethod
    def _normalize_difficulty(val: Any) -> str:
        if not val:
            return "medium"
        s = str(val).lower().strip()
        if s in ("easy", "simple", "low"):
            return "easy"
        elif s in ("hard", "complex", "high", "difficult"):
            return "hard"
        return "medium"

    @staticmethod
    def _parse_context(val: Any) -> List[str]:
        if not val:
            return []
        if isinstance(val, list):
            return [str(item).strip() for item in val if str(item).strip()]
        if isinstance(val, str):
            s = val.strip()
            if s.startswith("[") and s.endswith("]"):
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, list):
                        return [str(x).strip() for x in parsed if str(x).strip()]
                except Exception:
                    pass
            # Split by comma or semicolon
            return [part.strip() for part in re.split(r"[,;]+", s) if part.strip()]
        return [str(val)]

    @classmethod
    def parse_json(cls, content: bytes) -> Tuple[List[EvaluationCaseCreate], DatasetUploadSummary]:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")

        try:
            raw_data = json.loads(text)
        except json.JSONDecodeError as e:
            raise DatasetValidationError(f"Invalid JSON syntax: line {e.lineno} column {e.colno} ({e.msg})")

        # Handle object with a list property (e.g. {"cases": [...]})
        if isinstance(raw_data, dict):
            for key in ("cases", "data", "items", "evaluation_cases", "questions"):
                if key in raw_data and isinstance(raw_data[key], list):
                    raw_data = raw_data[key]
                    break
            else:
                # Single case dictionary
                raw_data = [raw_data]

        if not isinstance(raw_data, list):
            raise DatasetValidationError("JSON root must be an array of evaluation case objects.")

        valid_cases: List[EvaluationCaseCreate] = []
        seen_questions = set()
        duplicate_count = 0
        skipped_empty = 0
        warnings: List[str] = []
        errors: List[str] = []

        for idx, row in enumerate(raw_data, start=1):
            if not isinstance(row, dict):
                errors.append(f"Row {idx}: Expected JSON object, got {type(row).__name__}")
                continue

            # Check if row is empty
            if not any(bool(v) for v in row.values()):
                skipped_empty += 1
                continue

            # Extract question
            q = str(row.get("question") or row.get("query") or row.get("prompt") or "").strip()
            if not q:
                errors.append(f"Row {idx}: Missing required 'question' field.")
                continue

            q_key = q.lower()
            if q_key in seen_questions:
                duplicate_count += 1
                warnings.append(f"Row {idx}: Duplicate question detected: '{q[:50]}...'")
            else:
                seen_questions.add(q_key)

            ans = row.get("expected_answer") or row.get("ground_truth") or row.get("answer")
            ans_str = str(ans).strip() if ans is not None else None

            ctx_raw = row.get("expected_context") or row.get("context") or row.get("sources")
            ctx_list = cls._parse_context(ctx_raw)

            cat = str(row.get("category") or row.get("type") or "general").strip()
            diff = cls._normalize_difficulty(row.get("difficulty") or row.get("level"))
            meta = row.get("metadata") or row.get("case_metadata") or {}
            if not isinstance(meta, dict):
                meta = {"raw_metadata": str(meta)}

            valid_cases.append(
                EvaluationCaseCreate(
                    question=q,
                    expected_answer=ans_str,
                    expected_context=ctx_list,
                    category=cat or "general",
                    difficulty=diff,
                    case_metadata=meta
                )
            )

        if not valid_cases and errors:
            raise DatasetValidationError("Failed to parse evaluation cases.", errors=errors)

        summary = DatasetUploadSummary(
            dataset_id=uuid.uuid4(),
            version_id=uuid.uuid4(),
            version=1,
            total_parsed=len(raw_data),
            valid_cases_added=len(valid_cases),
            duplicate_count=duplicate_count,
            skipped_empty_rows=skipped_empty,
            warnings=warnings,
            errors=errors
        )
        return valid_cases, summary

    @classmethod
    def parse_csv(cls, content: bytes) -> Tuple[List[EvaluationCaseCreate], DatasetUploadSummary]:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")

        # Strip null bytes
        text = text.replace("\x00", "")
        f = io.StringIO(text)
        
        try:
            reader = csv.DictReader(f)
        except Exception as e:
            raise DatasetValidationError(f"Invalid CSV structure: {str(e)}")

        if not reader.fieldnames:
            raise DatasetValidationError("CSV file is empty or has no header columns.")

        # Map lowercased headers
        field_map = {fn.strip().lower(): fn for fn in reader.fieldnames if fn}
        
        # Locate question column
        q_col = None
        for candidate in ("question", "query", "prompt", "text", "q"):
            if candidate in field_map:
                q_col = field_map[candidate]
                break

        if not q_col:
            raise DatasetValidationError(
                f"Missing required 'question' column in CSV headers. Found headers: {list(field_map.keys())}"
            )

        ans_col = next((field_map[c] for c in ("expected_answer", "ground_truth", "answer", "target") if c in field_map), None)
        ctx_col = next((field_map[c] for c in ("expected_context", "context", "sources", "documents") if c in field_map), None)
        cat_col = next((field_map[c] for c in ("category", "type", "tag") if c in field_map), None)
        diff_col = next((field_map[c] for c in ("difficulty", "level", "complexity") if c in field_map), None)

        valid_cases: List[EvaluationCaseCreate] = []
        seen_questions = set()
        duplicate_count = 0
        skipped_empty = 0
        total_rows = 0
        warnings: List[str] = []
        errors: List[str] = []

        for idx, row in enumerate(reader, start=2): # 1 is header
            total_rows += 1
            if not row or not any(bool(v and str(v).strip()) for v in row.values()):
                skipped_empty += 1
                continue

            q = str(row.get(q_col) or "").strip()
            if not q:
                errors.append(f"Line {idx}: Missing question content.")
                continue

            q_key = q.lower()
            if q_key in seen_questions:
                duplicate_count += 1
                warnings.append(f"Line {idx}: Duplicate question: '{q[:50]}...'")
            else:
                seen_questions.add(q_key)

            ans_str = str(row.get(ans_col)).strip() if ans_col and row.get(ans_col) is not None else None
            ctx_list = cls._parse_context(row.get(ctx_col)) if ctx_col else []
            cat = str(row.get(cat_col) or "general").strip() if cat_col else "general"
            diff = cls._normalize_difficulty(row.get(diff_col)) if diff_col else "medium"

            # Custom extra metadata columns
            standard_cols = {q_col, ans_col, ctx_col, cat_col, diff_col}
            meta = {k: v.strip() for k, v in row.items() if k not in standard_cols and v and v.strip()}

            valid_cases.append(
                EvaluationCaseCreate(
                    question=q,
                    expected_answer=ans_str,
                    expected_context=ctx_list,
                    category=cat or "general",
                    difficulty=diff,
                    case_metadata=meta
                )
            )

        if not valid_cases and errors:
            raise DatasetValidationError("Failed to parse evaluation cases from CSV.", errors=errors)

        summary = DatasetUploadSummary(
            dataset_id=uuid.uuid4(),
            version_id=uuid.uuid4(),
            version=1,
            total_parsed=total_rows,
            valid_cases_added=len(valid_cases),
            duplicate_count=duplicate_count,
            skipped_empty_rows=skipped_empty,
            warnings=warnings,
            errors=errors
        )
        return valid_cases, summary

class DatasetService:
    @staticmethod
    async def create_dataset_with_version(
        project_id: UUID,
        name: str,
        description: Optional[str],
        cases: Optional[List[EvaluationCaseCreate]],
        db: AsyncSession
    ) -> Dataset:
        dataset = Dataset(
            project_id=project_id,
            name=name,
            description=description
        )
        db.add(dataset)
        await db.flush()

        if cases:
            version = DatasetVersion(
                dataset_id=dataset.id,
                version=1,
                case_count=len(cases),
                description="Initial dataset version"
            )
            db.add(version)
            await db.flush()

            db_cases = [
                EvaluationCase(
                    dataset_version_id=version.id,
                    question=c.question,
                    expected_answer=c.expected_answer,
                    expected_context=c.expected_context or [],
                    category=c.category,
                    difficulty=c.difficulty,
                    case_metadata=c.case_metadata or {}
                )
                for c in cases
            ]
            db.add_all(db_cases)

        await db.commit()
        await db.refresh(dataset)
        return dataset

    @staticmethod
    async def add_dataset_version(
        dataset_id: UUID,
        cases: List[EvaluationCaseCreate],
        description: Optional[str],
        db: AsyncSession
    ) -> DatasetVersion:
        # Determine next version number
        res = await db.execute(
            select(func.coalesce(func.max(DatasetVersion.version), 0)).where(DatasetVersion.dataset_id == dataset_id)
        )
        next_version = res.scalar_one() + 1

        version = DatasetVersion(
            dataset_id=dataset_id,
            version=next_version,
            case_count=len(cases),
            description=description or f"Version {next_version}"
        )
        db.add(version)
        await db.flush()

        db_cases = [
            EvaluationCase(
                dataset_version_id=version.id,
                question=c.question,
                expected_answer=c.expected_answer,
                expected_context=c.expected_context or [],
                category=c.category,
                difficulty=c.difficulty,
                case_metadata=c.case_metadata or {}
            )
            for c in cases
        ]
        db.add_all(db_cases)
        await db.commit()
        await db.refresh(version)
        return version

    @staticmethod
    async def get_version_statistics(
        version_id: UUID,
        db: AsyncSession
    ) -> DatasetStatistics:
        res = await db.execute(
            select(EvaluationCase).where(EvaluationCase.dataset_version_id == version_id)
        )
        cases = res.scalars().all()

        categories: Dict[str, int] = {}
        difficulties: Dict[str, int] = {}
        has_ans = 0
        has_ctx = 0

        for c in cases:
            categories[c.category] = categories.get(c.category, 0) + 1
            difficulties[c.difficulty] = difficulties.get(c.difficulty, 0) + 1
            if c.expected_answer and c.expected_answer.strip():
                has_ans += 1
            if c.expected_context and len(c.expected_context) > 0:
                has_ctx += 1

        return DatasetStatistics(
            total_cases=len(cases),
            categories=categories,
            difficulties=difficulties,
            has_expected_answer_count=has_ans,
            has_expected_context_count=has_ctx
        )
