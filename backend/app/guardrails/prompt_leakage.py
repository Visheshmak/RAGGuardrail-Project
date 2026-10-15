import re
from typing import Any, Dict, List, Optional, Pattern
from app.guardrails.base import (
    BaseGuardrail,
    GuardrailResult,
    GuardrailSeverity,
    GuardrailTarget,
    GuardrailType,
)


class PromptLeakageGuardrail(BaseGuardrail):
    """Detector for attempts to expose internal prompts, system instructions, secrets, or configuration."""

    name = "prompt_leakage"
    guardrail_type = GuardrailType.PROMPT_LEAKAGE
    description = "Detects attempts or responses leaking system instructions, configuration, or credentials"
    target = GuardrailTarget.BOTH

    # Extraction patterns in input queries
    EXTRACTION_PATTERNS: List[Pattern[str]] = [
        re.compile(r"\b(?:show|reveal|display|output|print|give\s+me|expose|leak|what\s+is|repeat|tell\s+me)\s+(?:me\s+)?(?:the\s+|your\s+|all\s+|exact\s+|hidden\s+|internal\s+)*(?:system\s+prompt|system\s+instructions?|developer\s+prompt|internal\s+instructions?|hidden\s+prompt|initial\s+rules|system\s+directives)\b", re.IGNORECASE),
        re.compile(r"\b(?:what\s+are|tell\s+me)\s+(?:me\s+)?(?:your\s+|the\s+)*(?:exact\s+|hidden\s+|initial\s+|system\s+)*(?:system\s+instructions|instructions\s+verbatim|initial\s+rules|system\s+directives|developer\s+instructions)\b", re.IGNORECASE),
        re.compile(r"\b(?:print|show|output|leak|reveal|dump|give\s+me)\s+(?:me\s+)?(?:the\s+|your\s+)*(?:database\s+password|secret\s+key|api\s+key|environment\s+variables?|\.env(?:\s+file)?|credentials?)\b", re.IGNORECASE),
        re.compile(r"\b(?:dump|reveal|show|expose)\s+(?:the\s+|your\s+)*(?:configuration|config\s+file|connection\s+string|db\s+password)\b", re.IGNORECASE),
        re.compile(r"\b(?:repeat|recite|print)\s+(?:all\s+)?text\s+before\s+(?:the\s+)?(?:first\s+)?(?:user\s+query|this\s+message|this\s+line)\b", re.IGNORECASE),
    ]

    # Secret and credential leakage patterns in output text
    SECRET_LEAKAGE_PATTERNS: List[Pattern[str]] = [
        re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,})\b"),  # OpenAI-like API keys
        re.compile(r"\b(?:ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{50,})\b"),  # GitHub tokens
        re.compile(r"\b(?:postgres(?:ql)?|mysql|mongodb|redis)://[A-Za-z0-9_]+:[^@\s]+@[^\s]+\b", re.IGNORECASE),  # DB connection URLs with passwords
        re.compile(r"\b(?:AWS_SECRET_ACCESS_KEY|SECRET_KEY|JWT_SECRET|OPENAI_API_KEY)\s*=\s*['\"][^\s'\"]+['\"]", re.IGNORECASE),
        re.compile(r"BEGIN\s+(?:RSA|OPENSSH|DSA|EC)?\s*PRIVATE\s+KEY", re.IGNORECASE),
        re.compile(r"<\s*system\s*>\s*You\s+are\s+a\s+helpful\s+and\s+precise\s+organizational\s+AI\s+assistant", re.IGNORECASE),
    ]

    def __init__(
        self,
        severity_override: Optional[GuardrailSeverity] = None,
        custom_leakage_patterns: Optional[List[str]] = None,
    ):
        self.severity_override = severity_override
        self.custom_compiled: List[Pattern[str]] = []
        if custom_leakage_patterns:
            for pat in custom_leakage_patterns:
                try:
                    self.custom_compiled.append(re.compile(pat, re.IGNORECASE))
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
                reason="Text is empty",
                metadata={"findings": []}
            )

        context = context or {}
        is_output = context.get("is_output", False)
        known_system_prompt = context.get("system_prompt")

        findings: List[Dict[str, Any]] = []

        # Check 1: Extraction patterns (predominantly for inputs)
        for pat in self.EXTRACTION_PATTERNS:
            match = pat.search(text)
            if match:
                findings.append({
                    "category": "prompt_extraction_request",
                    "matched": match.group(),
                    "severity": GuardrailSeverity.HIGH
                })

        # Check 2: Secret & credential leakage (predominantly for outputs)
        for pat in self.SECRET_LEAKAGE_PATTERNS:
            match = pat.search(text)
            if match:
                findings.append({
                    "category": "credential_or_key_leakage",
                    "matched": "[REDACTED_CREDENTIAL]",
                    "severity": GuardrailSeverity.CRITICAL
                })

        # Check 3: Custom patterns
        for pat in self.custom_compiled:
            match = pat.search(text)
            if match:
                findings.append({
                    "category": "custom_leakage_pattern",
                    "matched": match.group(),
                    "severity": GuardrailSeverity.HIGH
                })

        # Check 4: Verbatim leakage of known system prompt if supplied
        if is_output and known_system_prompt and len(known_system_prompt) > 20:
            # Check if large phrases (>30 chars) of system prompt are leaked verbatim
            phrases = [p.strip() for p in known_system_prompt.split(".") if len(p.strip()) > 25]
            for phrase in phrases:
                if phrase.lower() in text.lower():
                    findings.append({
                        "category": "system_prompt_verbatim_leakage",
                        "matched": phrase[:50] + "...",
                        "severity": GuardrailSeverity.CRITICAL
                    })
                    break

        if findings:
            has_critical = any(f["severity"] == GuardrailSeverity.CRITICAL for f in findings)
            severity = self.severity_override or (GuardrailSeverity.CRITICAL if has_critical else GuardrailSeverity.HIGH)
            categories = list({f["category"] for f in findings})
            reason = f"Prompt leakage violation detected: [{', '.join(categories)}]"

            return GuardrailResult(
                guardrail=self.name,
                passed=False,
                severity=severity,
                reason=reason,
                metadata={
                    "findings_count": len(findings),
                    "categories": categories,
                    "findings": findings
                }
            )

        return GuardrailResult(
            guardrail=self.name,
            passed=True,
            severity=GuardrailSeverity.LOW,
            reason="No prompt leakage detected",
            metadata={"findings": []}
        )
