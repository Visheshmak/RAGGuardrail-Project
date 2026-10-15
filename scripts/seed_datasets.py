import asyncio
import os
import sys
import json
from pathlib import Path

# Add backend directory to sys.path
backend_dir = str(Path(__file__).parent.parent / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.user import User
from app.models.project import Project
from app.models.dataset import Dataset, DatasetVersion
from app.services.dataset_service import DatasetService, DatasetParser

DATASETS_DIR = Path(__file__).parent.parent / "data" / "datasets"

async def seed_datasets():
    print("=" * 60)
    print(" RAGGuard — Seed Evaluation Datasets")
    print("=" * 60)

    async with async_session_maker() as session:
        # Find demo project
        res = await session.execute(
            select(Project).where(Project.name == "Enterprise HR & Compliance Knowledge Base")
        )
        project = res.scalar_one_or_none()
        if not project:
            # Fallback to any project
            res = await session.execute(select(Project).limit(1))
            project = res.scalar_one_or_none()
            if not project:
                print("[!] No project found. Please run seed_documents.py first.")
                return

        print(f"[*] Seeding datasets into project '{project.name}' (ID: {project.id})...")

        # 1. Seed Core HR Benchmark Dataset from JSON
        json_file = DATASETS_DIR / "demo_evaluation_cases.json"
        if json_file.exists():
            ds_name = "Enterprise Policy Core Benchmark"
            res = await session.execute(
                select(Dataset).where(Dataset.project_id == project.id, Dataset.name == ds_name)
            )
            dataset = res.scalar_one_or_none()
            if not dataset:
                print(f"[+] Importing '{ds_name}' from {json_file.name}...")
                cases, summary = DatasetParser.parse_json(json_file.read_bytes())
                dataset = await DatasetService.create_dataset_with_version(
                    project_id=project.id,
                    name=ds_name,
                    description="Curated benchmark set with normal, ambiguous, out-of-domain, and multi-doc questions.",
                    cases=cases,
                    db=session
                )
                print(f"    [✓] Created dataset '{ds_name}' with {len(cases)} cases in v1.")
            else:
                print(f"    [*] Dataset '{ds_name}' already exists.")

        # 2. Seed Regression Test Dataset from CSV
        csv_file = DATASETS_DIR / "demo_evaluation_cases.csv"
        if csv_file.exists():
            csv_ds_name = "Compliance & Benefits Regression Suite"
            res = await session.execute(
                select(Dataset).where(Dataset.project_id == project.id, Dataset.name == csv_ds_name)
            )
            csv_dataset = res.scalar_one_or_none()
            if not csv_dataset:
                print(f"[+] Importing '{csv_ds_name}' from {csv_file.name}...")
                csv_cases, csv_summary = DatasetParser.parse_csv(csv_file.read_bytes())
                csv_dataset = await DatasetService.create_dataset_with_version(
                    project_id=project.id,
                    name=csv_ds_name,
                    description="Standard test suite for automated regression detection.",
                    cases=csv_cases,
                    db=session
                )
                print(f"    [✓] Created dataset '{csv_ds_name}' with {len(csv_cases)} cases in v1.")
            else:
                print(f"    [*] Dataset '{csv_ds_name}' already exists.")

        print("\n[✓] Evaluation dataset seeding completed successfully!")

if __name__ == "__main__":
    asyncio.run(seed_datasets())
