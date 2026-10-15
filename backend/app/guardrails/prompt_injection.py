import re
from typing import Any, Dict, List, Optional, Pattern
from app.guardrails.base import (
    BaseGuardrail,
    GuardrailResult,
    GuardrailSeverity,
    GuardrailTarget,
    GuardrailType,
)


class PromptInjectionGuardrail(BaseGuardrail):
    """Layered detector for prompt injection, jailbreaks, and adversarial overrides."""

    name = "prompt_injection"
    guardrail_type = GuardrailType.PROMPT_INJECTION
    description = "Detects prompt injection attempts, roleplay jailbreaks, and system overrides"
    target = GuardrailTarget.INPUT

    # Layer 1: Core Instruction Overrides & Jailbreak Phrases (High confidence)
    LAYER_1_PATTERNS: List[Pattern[str]] = [
        re.compile(r"\bignore\s+(?:all\s+)?(?:(?:previous|prior|above|earlier|system|existing|current)\s+)?(?:instructions|prompts|rules|guidelines|directives)\b", re.IGNORECASE),
        re.compile(r"\bdisregard\s+(?:all\s+)?(?:(?:previous|prior|above|earlier|system|existing|current)\s+)?(?:instructions|prompts|rules|guidelines|directives)\b", re.IGNORECASE),
        re.compile(r"\bforget\s+(?:all\s+)?(?:(?:previous|prior|above|earlier|your|system|existing|current)\s+)?(?:instructions|prompts|rules|guidelines|context)\b", re.IGNORECASE),
        re.compile(r"\boverride\s+(?:all\s+)?(?:(?:system|safety|security|prior)\s+)?(?:rules|prompts|instructions|guidelines|filters)\b", re.IGNORECASE),
        re.compile(r"\bbypass\s+(?:all\s+)?(?:(?:safety|security|content|guardrail|system)\s+)?(?:rules|filters|guidelines|mechanisms)\b", re.IGNORECASE),
        re.compile(r"\bnow\s+you\s+are\s+(?:DAN|unrestricted|jailbroken|freed|an\s+AI\s+without\s+rules|in\s+developer\s+mode)\b", re.IGNORECASE),
        re.compile(r"\bdo\s+anything\s+now\b", re.IGNORECASE),
        re.compile(r"\bdeveloper\s+mode\s+(?:enabled|activated|on)\b", re.IGNORECASE),
        re.compile(r"\bpretend\s+you\s+have\s+no\s+(?:rules|restrictions|limits|guidelines)\b", re.IGNORECASE),
        re.compile(r"\byou\s+are\s+no\s+longer\s+bound\s+by\b", re.IGNORECASE),
        re.compile(r"\bignore\s+safety\s+rules\b", re.IGNORECASE),
        re.compile(r"\breveal\s+(?:confidential|classified|secret)\s+information\b", re.IGNORECASE),
    ]

    # Layer 2: Structural & Delimiter Hijacking (System prompt emulation)
    LAYER_2_PATTERNS: List[Pattern[str]] = [
        re.compile(r"<\s*system\s*>.*?</\s*system\s*>", re.IGNORECASE | re.DOTALL),
        re.compile(r"\[\s*INST\s*\]\s*<<SYS>>", re.IGNORECASE),
        re.compile(r"<\|im_start\|>\s*system", re.IGNORECASE),
        re.compile(r"^#+\s*(?:System\s+Prompt|System\s+Directive|Admin\s+Override)", re.IGNORECASE | re.MULTILINE),
        re.compile(r"(?:\n|^)(?:System|Admin|Root|Developer):\s*(?:You\s+are|Override|Execute|Forget)", re.IGNORECASE),
        re.compile(r"```(?:system|admin|override)\s*\n", re.IGNORECASE),
    ]

    # Layer 3: Extraction & Evasion Markers
    LAYER_3_PATTERNS: List[Pattern[str]] = [
        re.compile(r"\bprint\s+(?:your\s+)?(?:initial|first|system|hidden)\s+(?:prompt|instructions|directive)\b", re.IGNORECASE),
        re.compile(r"\boutput\s+(?:the\s+)?(?:system\s+prompt|raw\s+instructions)\b", re.IGNORECASE),
        re.compile(r"\brepeat\s+(?:everything\s+)?above\s+verbatim\b", re.IGNORECASE),
        re.compile(r"\bshow\s+me\s+your\s+(?:exact\s+)?system\s+prompt\b", re.IGNORECASE),
        re.compile(r"\brepeat\s+all\s+text\s+before\s+this\s+line\b", re.IGNORECASE),
    ]

    def __init__(
        self,
        custom_patterns: Optional[List[str]] = None,
        severity_override: Optional[GuardrailSeverity] = None,
    ):
        self.custom_compiled: List[Pattern[str]] = []
        if custom_patterns:
            for pat in custom_patterns:
                try:
                    self.custom_compiled.append(re.compile(pat, re.IGNORECASE))
                except re.error:
                    pass
        self.severity_override = severity_override

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
                metadata={"matches": []}
            )

        matches: List[Dict[str, Any]] = []
        risk_score = 0.0

        # Layer 1 check (High weight: 0.9)
        for pattern in self.LAYER_1_PATTERNS:
            found = pattern.findall(text)
            if found:
                matches.append({"layer": "instruction_override", "pattern": pattern.pattern, "matched": found})
                risk_score = max(risk_score, 0.95)

        # Layer 2 check (Delimiter hijacking weight: 0.85)
        for pattern in self.LAYER_2_PATTERNS:
            found = pattern.findall(text)
            if found:
                matches.append({"layer": "delimiter_hijacking", "pattern": pattern.pattern, "matched": found})
                risk_score = max(risk_score, 0.85)

        # Layer 3 check (System extraction weight: 0.80)
        for pattern in self.LAYER_3_PATTERNS:
            found = pattern.findall(text)
            if found:
                matches.append({"layer": "system_extraction", "pattern": pattern.pattern, "matched": found})
                risk_score = max(risk_score, 0.80)

        # Custom patterns check
        for pattern in self.custom_compiled:
            found = pattern.findall(text)
            if found:
                matches.append({"layer": "custom_rule", "pattern": pattern.pattern, "matched": found})
                risk_score = max(risk_score, 0.90)

        if matches:
            # Determine severity
            if risk_score >= 0.9:
                severity = self.severity_override or GuardrailSeverity.CRITICAL
            else:
                severity = self.severity_override or GuardrailSeverity.HIGH

            matched_descriptions = [f"{m['layer']}: '{m['matched'][0]}'" for m in matches[:3]]
            reason = f"Prompt injection attempt detected ({', '.join(matched_descriptions)})"

            return GuardrailResult(
                guardrail=self.name,
                passed=False,
                severity=severity,
                reason=reason,
                metadata={
                    "risk_score": risk_score,
                    "match_count": len(matches),
                    "matches": matches,
                }
            )

        return GuardrailResult(
            guardrail=self.name,
            passed=True,
            severity=GuardrailSeverity.LOW,
            reason="No prompt injection patterns detected",
            metadata={"risk_score": 0.0, "matches": []}
        )
