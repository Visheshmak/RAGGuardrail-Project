import re
from typing import Any, Dict, List, Optional, Pattern, Protocol
from app.guardrails.base import (
    BaseGuardrail,
    GuardrailResult,
    GuardrailSeverity,
    GuardrailTarget,
    GuardrailType,
)


class SafetyModelEvaluator(Protocol):
    """Protocol for optional pluggable model-based safety evaluators."""

    async def evaluate_safety(self, text: str) -> Dict[str, Any]:
        """Returns dict with: is_safe (bool), category (str), confidence (float), reason (str)"""
        ...


class SafetyGuardrail(BaseGuardrail):
    """Pluggable safety and toxicity guardrail with deterministic baseline and optional model evaluator."""

    name = "safety"
    guardrail_type = GuardrailType.SAFETY
    description = "Detects toxicity, hate speech, violence, self-harm, harassment, and unsafe content"
    target = GuardrailTarget.BOTH

    # Categorized deterministic safety patterns
    SAFETY_CATEGORIES: Dict[str, Dict[str, Any]] = {
        "self_harm": {
            "severity": GuardrailSeverity.CRITICAL,
            "patterns": [
                re.compile(r"\b(?:how\s+to\s+commit\s+suicide|kill\s+myself|ways\s+to\s+hang\s+myself|methods\s+of\s+self-harm|instruction\s+for\s+overdose)\b", re.IGNORECASE),
                re.compile(r"\b(?:encourage|promote)\s+(?:suicide|self-harm|cutting\s+wrists)\b", re.IGNORECASE),
            ]
        },
        "violence_and_threats": {
            "severity": GuardrailSeverity.CRITICAL,
            "patterns": [
                re.compile(r"\b(?:how\s+to\s+build\s+a\s+bomb|make\s+an\s+explosive|synthesize\s+ricin|create\s+anthrax)\b", re.IGNORECASE),
                re.compile(r"\b(?:i\s+will\s+kill\s+you|threaten\s+to\s+murder|plan\s+a\s+mass\s+shooting)\b", re.IGNORECASE),
                re.compile(r"\b(?:instructions\s+to\s+assassinate|weaponize\s+biological\s+agent)\b", re.IGNORECASE),
            ]
        },
        "hate_speech": {
            "severity": GuardrailSeverity.HIGH,
            "patterns": [
                re.compile(r"\b(?:subhuman\s+scum|exterminate\s+all\s+[a-z]+|racial\s+cleansing|genocide\s+is\s+good)\b", re.IGNORECASE),
                re.compile(r"\b(?:all\s+[a-z]+\s+should\s+be\s+(?:killed|deported|hanged|burned))\b", re.IGNORECASE),
            ]
        },
        "harassment_and_abuse": {
            "severity": GuardrailSeverity.HIGH,
            "patterns": [
                re.compile(r"\b(?:doxx\s+someone|leak\s+personal\s+address\s+to\s+harass|stalk\s+someone's\s+family)\b", re.IGNORECASE),
                re.compile(r"\b(?:swat\s+their\s+house|coordinate\s+harassment\s+campaign)\b", re.IGNORECASE),
            ]
        },
        "severe_profanity_and_vulgarity": {
            "severity": GuardrailSeverity.MEDIUM,
            "patterns": [
                re.compile(r"\b(?:fuck\s+you|motherfucker|cunt|bastard|piece\s+of\s+shit|go\s+die)\b", re.IGNORECASE),
            ]
        }
    }

    def __init__(
        self,
        model_evaluator: Optional[SafetyModelEvaluator] = None,
        enabled_categories: Optional[List[str]] = None,
        severity_override: Optional[GuardrailSeverity] = None,
        custom_safety_patterns: Optional[Dict[str, List[str]]] = None,
    ):
        self.model_evaluator = model_evaluator
        self.enabled_categories = enabled_categories or list(self.SAFETY_CATEGORIES.keys())
        self.severity_override = severity_override

        self.custom_compiled: Dict[str, List[Pattern[str]]] = {}
        if custom_safety_patterns:
            for cat, pats in custom_safety_patterns.items():
                self.custom_compiled[cat] = []
                for p in pats:
                    try:
                        self.custom_compiled[cat].append(re.compile(p, re.IGNORECASE))
                    except re.error:
                        pass

    async def check(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> GuardrailResult:
        if not text or not text.strip():
            return GuardrailResult(
                guardrail=self.name,
                passed=True,
                severity=GuardrailSeverity.LOW,
                reason="Input text is empty",
                metadata={"violations": []}
            )

        violations: List[Dict[str, Any]] = []

        # 1. Deterministic baseline check
        for category_name in self.enabled_categories:
            cat_data = self.SAFETY_CATEGORIES.get(category_name)
            if not cat_data:
                continue

            patterns = cat_data["patterns"]
            cat_severity = cat_data["severity"]

            for pat in patterns:
                match = pat.search(text)
                if match:
                    violations.append({
                        "category": category_name,
                        "matched": match.group(),
                        "severity": cat_severity,
                        "evaluator": "deterministic"
                    })

        # 2. Custom patterns
        for cat_name, pats in self.custom_compiled.items():
            for pat in pats:
                match = pat.search(text)
                if match:
                    violations.append({
                        "category": f"custom_{cat_name}",
                        "matched": match.group(),
                        "severity": GuardrailSeverity.HIGH,
                        "evaluator": "deterministic_custom"
                    })

        # 3. Model-based evaluator (if attached)
        if self.model_evaluator and not violations:
            try:
                model_result = await self.model_evaluator.evaluate_safety(text)
                if not model_result.get("is_safe", True):
                    violations.append({
                        "category": model_result.get("category", "unsafe_content"),
                        "matched": "model_classification",
                        "severity": GuardrailSeverity.HIGH,
                        "evaluator": "model_based",
                        "confidence": model_result.get("confidence", 0.9),
                        "reason": model_result.get("reason", "Model safety classifier flagged input")
                    })
            except Exception as e:
                # Log model error and continue without blocking
                pass

        if violations:
            has_critical = any(v["severity"] == GuardrailSeverity.CRITICAL for v in violations)
            has_high = any(v["severity"] == GuardrailSeverity.HIGH for v in violations)

            if has_critical:
                max_sev = GuardrailSeverity.CRITICAL
            elif has_high:
                max_sev = GuardrailSeverity.HIGH
            else:
                max_sev = GuardrailSeverity.MEDIUM

            severity = self.severity_override or max_sev
            cats = list({v["category"] for v in violations})
            reason = f"Safety policy violation: detected unsafe content in [{', '.join(cats)}]"

            return GuardrailResult(
                guardrail=self.name,
                passed=False,
                severity=severity,
                reason=reason,
                metadata={
                    "violation_count": len(violations),
                    "categories": cats,
                    "violations": violations
                }
            )

        return GuardrailResult(
            guardrail=self.name,
            passed=True,
            severity=GuardrailSeverity.LOW,
            reason="Safety check passed: no toxic or unsafe content detected",
            metadata={"violations": []}
        )
