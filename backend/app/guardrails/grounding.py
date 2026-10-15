import re
from typing import Any, Dict, List, Optional, Set
from app.guardrails.base import (
    BaseGuardrail,
    GuardrailResult,
    GuardrailSeverity,
    GuardrailTarget,
    GuardrailType,
)


def _tokenize_and_normalize(text: str) -> Set[str]:
    """Tokenize and filter stop words for keyword overlap check."""
    stop_words = {
        "a", "an", "the", "and", "or", "but", "if", "because", "as", "what",
        "which", "this", "that", "these", "those", "then", "just", "so", "than",
        "such", "both", "through", "about", "for", "is", "of", "while", "during",
        "to", "from", "in", "out", "on", "off", "again", "further", "then", "once",
        "here", "there", "when", "where", "why", "how", "all", "any", "both",
        "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not",
        "only", "own", "same", "so", "than", "too", "very", "can", "will", "just",
        "don", "should", "now", "are", "was", "were", "be", "been", "being", "have",
        "has", "had", "having", "do", "does", "did", "doing", "would", "could"
    }
    words = re.findall(r"\b[A-Za-z0-9_$%-]{2,}\b", text.lower())
    return {w for w in words if w not in stop_words}


def _split_into_claims(text: str) -> List[str]:
    """Split text into individual sentences/claims."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 5]


class GroundingGuardrail(BaseGuardrail):
    """Evaluates whether generated answers are factually supported by retrieved context."""

    name = "grounding"
    guardrail_type = GuardrailType.GROUNDING
    description = "Checks that generated answers are grounded in and supported by retrieved context"
    target = GuardrailTarget.OUTPUT

    def __init__(
        self,
        grounding_threshold: float = 0.5,
        llm_provider: Optional[Any] = None,
        severity_override: Optional[GuardrailSeverity] = None,
    ):
        self.grounding_threshold = grounding_threshold
        self.llm_provider = llm_provider
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
                reason="Generated answer is empty",
                metadata={"grounding_score": 1.0}
            )

        context = context or {}
        retrieved_contexts: List[str] = []

        # Handle different context formats
        raw_sources = context.get("retrieved_chunks") or context.get("sources") or context.get("context_snippets") or []
        if isinstance(raw_sources, list):
            for item in raw_sources:
                if isinstance(item, str):
                    retrieved_contexts.append(item)
                elif hasattr(item, "text"):
                    retrieved_contexts.append(item.text)
                elif isinstance(item, dict) and "text" in item:
                    retrieved_contexts.append(item["text"])
        elif isinstance(raw_sources, str):
            retrieved_contexts.append(raw_sources)

        if not retrieved_contexts:
            # If no context was retrieved, check if model accurately declined to answer
            decline_phrases = [
                "does not contain", "no relevant context", "cannot answer",
                "not provided in the context", "not enough information",
                "the provided documents do not", "no information available"
            ]
            if any(phrase in text.lower() for phrase in decline_phrases):
                return GuardrailResult(
                    guardrail=self.name,
                    passed=True,
                    severity=GuardrailSeverity.LOW,
                    reason="Model correctly abstained when no context was retrieved",
                    metadata={"grounding_score": 1.0, "abstained": True}
                )

            return GuardrailResult(
                guardrail=self.name,
                passed=False,
                severity=self.severity_override or GuardrailSeverity.HIGH,
                reason="Answer generated without any retrieved context (hallucination risk)",
                metadata={"grounding_score": 0.0, "unsupported_claims": [text]}
            )

        combined_context = " ".join(retrieved_contexts)
        context_tokens = _tokenize_and_normalize(combined_context)

        # Check claim by claim
        claims = _split_into_claims(text)
        if not claims:
            claims = [text]

        supported_claims: List[str] = []
        unsupported_claims: List[str] = []

        for claim in claims:
            claim_tokens = _tokenize_and_normalize(claim)
            if not claim_tokens:
                supported_claims.append(claim)
                continue

            # Check overlap of non-stop-word tokens and numbers/entities
            overlap = claim_tokens.intersection(context_tokens)
            overlap_ratio = len(overlap) / len(claim_tokens)

            # Extract numbers/currencies in claim (e.g. $750, 20 days, 3.12)
            claim_entities = set(re.findall(r"[\$€£]?\d+(?:\.\d+)?%?", claim))
            context_entities = set(re.findall(r"[\$€£]?\d+(?:\.\d+)?%?", combined_context))
            entity_unsupported = any(ent not in context_entities for ent in claim_entities)

            if overlap_ratio >= 0.4 and not entity_unsupported:
                supported_claims.append(claim)
            elif overlap_ratio >= 0.6:
                supported_claims.append(claim)
            else:
                unsupported_claims.append(claim)

        # Overall grounding score
        grounding_score = len(supported_claims) / max(len(claims), 1)

        # Evaluate against threshold
        passed = grounding_score >= self.grounding_threshold

        if not passed:
            severity = self.severity_override or (
                GuardrailSeverity.HIGH if grounding_score < 0.3 else GuardrailSeverity.MEDIUM
            )
            reason = (
                f"Grounding check failed: score {round(grounding_score, 2)} < threshold {self.grounding_threshold}. "
                f"{len(unsupported_claims)} unsupported claim(s) detected."
            )
        else:
            severity = GuardrailSeverity.LOW
            reason = f"Grounding check passed with score {round(grounding_score, 2)}."

        return GuardrailResult(
            guardrail=self.name,
            passed=passed,
            severity=severity,
            reason=reason,
            metadata={
                "grounding_score": round(grounding_score, 4),
                "threshold": self.grounding_threshold,
                "total_claims": len(claims),
                "supported_count": len(supported_claims),
                "unsupported_count": len(unsupported_claims),
                "unsupported_claims": unsupported_claims,
            }
        )
