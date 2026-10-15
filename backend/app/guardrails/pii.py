import re
from typing import Any, Dict, List, Optional, Pattern
from app.guardrails.base import (
    BaseGuardrail,
    GuardrailResult,
    GuardrailSeverity,
    GuardrailTarget,
    GuardrailType,
)


def is_valid_luhn(card_number_str: str) -> bool:
    """Validate card number using the Luhn checksum algorithm."""
    digits = [int(c) for c in card_number_str if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = d * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += d
    return checksum % 10 == 0


def is_valid_ipv4(ip_str: str) -> bool:
    """Validate IPv4 address components are in 0-255 range."""
    parts = ip_str.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except ValueError:
        return False


class PIIDetectionGuardrail(BaseGuardrail):
    """Deterministic detector for Personally Identifiable Information (PII)."""

    name = "pii_detection"
    guardrail_type = GuardrailType.PII_DETECTION
    description = "Detects emails, phone numbers, credit cards, IP addresses, SSNs, and custom PII"
    target = GuardrailTarget.BOTH

    # Regex patterns
    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    PHONE_PATTERN = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
    # Credit cards: 13-19 digits possibly separated by spaces or dashes
    CARD_CANDIDATE_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{1,4}\b|\b\d{13,19}\b")
    IPV4_PATTERN = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
    IPV6_PATTERN = re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b|\b(?:[0-9a-fA-F]{1,4}:){1,7}:[0-9a-fA-F]{1,4}\b")
    SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

    def __init__(
        self,
        detect_email: bool = True,
        detect_phone: bool = True,
        detect_credit_card: bool = True,
        detect_ip: bool = True,
        detect_ssn: bool = True,
        custom_patterns: Optional[Dict[str, str]] = None,
        severity_override: Optional[GuardrailSeverity] = None,
    ):
        self.detect_email = detect_email
        self.detect_phone = detect_phone
        self.detect_credit_card = detect_credit_card
        self.detect_ip = detect_ip
        self.detect_ssn = detect_ssn
        self.severity_override = severity_override

        self.custom_compiled: Dict[str, Pattern[str]] = {}
        if custom_patterns:
            for label, pat_str in custom_patterns.items():
                try:
                    self.custom_compiled[label] = re.compile(pat_str, re.IGNORECASE)
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
                metadata={"pii_found": []}
            )

        found_entities: List[Dict[str, Any]] = []

        # 1. Email detection
        if self.detect_email:
            for match in self.EMAIL_PATTERN.finditer(text):
                found_entities.append({
                    "type": "email",
                    "value": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "severity": GuardrailSeverity.MEDIUM
                })

        # 2. Phone detection
        if self.detect_phone:
            for match in self.PHONE_PATTERN.finditer(text):
                val = match.group()
                # Basic sanity filter to avoid matching pure small integers
                clean_digits = re.sub(r"\D", "", val)
                if len(clean_digits) >= 10:
                    found_entities.append({
                        "type": "phone",
                        "value": val,
                        "start": match.start(),
                        "end": match.end(),
                        "severity": GuardrailSeverity.MEDIUM
                    })

        # 3. Credit Card detection (with Luhn check)
        if self.detect_credit_card:
            for match in self.CARD_CANDIDATE_PATTERN.finditer(text):
                candidate = match.group()
                clean_num = re.sub(r"\D", "", candidate)
                if is_valid_luhn(clean_num):
                    found_entities.append({
                        "type": "credit_card",
                        "value": candidate,
                        "start": match.start(),
                        "end": match.end(),
                        "severity": GuardrailSeverity.HIGH
                    })

        # 4. IP Address detection
        if self.detect_ip:
            for match in self.IPV4_PATTERN.finditer(text):
                val = match.group()
                if is_valid_ipv4(val):
                    found_entities.append({
                        "type": "ipv4_address",
                        "value": val,
                        "start": match.start(),
                        "end": match.end(),
                        "severity": GuardrailSeverity.LOW
                    })
            for match in self.IPV6_PATTERN.finditer(text):
                found_entities.append({
                    "type": "ipv6_address",
                    "value": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "severity": GuardrailSeverity.LOW
                })

        # 5. SSN detection
        if self.detect_ssn:
            for match in self.SSN_PATTERN.finditer(text):
                found_entities.append({
                    "type": "ssn",
                    "value": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "severity": GuardrailSeverity.HIGH
                })

        # 6. Custom patterns
        for label, pat in self.custom_compiled.items():
            for match in pat.finditer(text):
                found_entities.append({
                    "type": f"custom_{label}",
                    "value": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                    "severity": GuardrailSeverity.HIGH
                })

        if found_entities:
            # Determine maximum severity
            has_high = any(e["severity"] == GuardrailSeverity.HIGH for e in found_entities)
            has_medium = any(e["severity"] == GuardrailSeverity.MEDIUM for e in found_entities)
            
            if has_high:
                max_sev = GuardrailSeverity.HIGH
            elif has_medium:
                max_sev = GuardrailSeverity.MEDIUM
            else:
                max_sev = GuardrailSeverity.LOW

            severity = self.severity_override or max_sev
            types_found = list({e["type"] for e in found_entities})
            reason = f"PII detected: found {len(found_entities)} instance(s) of [{', '.join(types_found)}]"

            return GuardrailResult(
                guardrail=self.name,
                passed=False,
                severity=severity,
                reason=reason,
                metadata={
                    "entity_count": len(found_entities),
                    "types": types_found,
                    "pii_found": [
                        {"type": e["type"], "masked": self._mask_value(e["value"], e["type"])}
                        for e in found_entities
                    ]
                }
            )

        return GuardrailResult(
            guardrail=self.name,
            passed=True,
            severity=GuardrailSeverity.LOW,
            reason="No PII detected",
            metadata={"entity_count": 0, "pii_found": []}
        )

    def redact(self, text: str) -> str:
        """Utility method to redact all detected PII in text."""
        redacted = text
        if self.detect_email:
            redacted = self.EMAIL_PATTERN.sub("[REDACTED_EMAIL]", redacted)
        if self.detect_ssn:
            redacted = self.SSN_PATTERN.sub("[REDACTED_SSN]", redacted)
        if self.detect_credit_card:
            def _replace_cc(match):
                c = match.group()
                if is_valid_luhn(re.sub(r"\D", "", c)):
                    return "[REDACTED_CREDIT_CARD]"
                return c
            redacted = self.CARD_CANDIDATE_PATTERN.sub(_replace_cc, redacted)
        if self.detect_phone:
            def _replace_phone(match):
                c = match.group()
                if len(re.sub(r"\D", "", c)) >= 10:
                    return "[REDACTED_PHONE]"
                return c
            redacted = self.PHONE_PATTERN.sub(_replace_phone, redacted)
        if self.detect_ip:
            def _replace_ip(match):
                c = match.group()
                if is_valid_ipv4(c):
                    return "[REDACTED_IP]"
                return c
            redacted = self.IPV4_PATTERN.sub(_replace_ip, redacted)
            redacted = self.IPV6_PATTERN.sub("[REDACTED_IP]", redacted)
        for label, pat in self.custom_compiled.items():
            redacted = pat.sub(f"[REDACTED_{label.upper()}]", redacted)
        return redacted

    def _mask_value(self, value: str, pii_type: str) -> str:
        if pii_type == "email":
            parts = value.split("@")
            if len(parts) == 2:
                name, domain = parts
                masked_name = name[0] + "***" if len(name) > 1 else "*"
                return f"{masked_name}@{domain}"
        elif pii_type == "credit_card":
            clean = re.sub(r"\D", "", value)
            return f"****-****-****-{clean[-4:]}" if len(clean) >= 4 else "****"
        elif pii_type == "ssn":
            return "***-**-" + value.split("-")[-1]
        elif pii_type == "phone":
            clean = re.sub(r"\D", "", value)
            return f"***-***-{clean[-4:]}" if len(clean) >= 4 else "***-***-****"
        return "[REDACTED]"
