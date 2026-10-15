import re
from typing import Any, Dict, List, Optional, Set
from app.guardrails.grounding import GroundingGuardrail


def _tokenize(text: str) -> Set[str]:
    stop_words = {
        "a", "an", "the", "and", "or", "but", "if", "because", "as", "what",
        "which", "this", "that", "these", "those", "then", "just", "so", "than",
        "such", "both", "through", "about", "for", "is", "of", "while", "during",
        "to", "from", "in", "out", "on", "off", "again", "further", "then", "once",
        "here", "there", "when", "where", "why", "how", "all", "any", "both",
        "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not",
        "only", "own", "same", "so", "than", "too", "very", "can", "will", "just",
        "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did"
    }
    words = re.findall(r"\b[A-Za-z0-9_$%-]{2,}\b", text.lower())
    return {w for w in words if w not in stop_words}


def compute_accuracy(actual_answer: str, expected_answer: Optional[str]) -> float:
    """Compute lexical and semantic overlap accuracy score between actual and expected answer."""
    if not expected_answer or not expected_answer.strip():
        return 1.0  # Open-ended if no golden ground truth answer given
    if not actual_answer or not actual_answer.strip():
        return 0.0

    actual_tokens = _tokenize(actual_answer)
    expected_tokens = _tokenize(expected_answer)

    if not expected_tokens:
        return 1.0

    overlap = actual_tokens.intersection(expected_tokens)
    recall = len(overlap) / len(expected_tokens)
    precision = len(overlap) / max(len(actual_tokens), 1)

    if recall + precision == 0:
        return 0.0

    f1 = (2 * precision * recall) / (precision + recall)
    return round(min(max(f1, 0.0), 1.0), 4)


def compute_retrieval_recall(
    retrieved_chunks: List[str],
    expected_context: Optional[List[str]] = None
) -> float:
    """Compute context recall: percentage of golden context snippets found in retrieved chunks."""
    if not expected_context:
        return 1.0  # If no specific context specified, assume full recall if chunks returned
    if not retrieved_chunks:
        return 0.0

    combined_retrieved = " ".join(retrieved_chunks).lower()
    retrieved_tokens = _tokenize(combined_retrieved)

    hits = 0
    total = len(expected_context)

    for expected_snippet in expected_context:
        exp_tokens = _tokenize(expected_snippet)
        if not exp_tokens:
            hits += 1
            continue
        overlap = exp_tokens.intersection(retrieved_tokens)
        if (len(overlap) / len(exp_tokens)) >= 0.5:
            hits += 1

    return round(hits / max(total, 1), 4)


async def compute_faithfulness(
    actual_answer: str,
    retrieved_chunks: List[str]
) -> float:
    """Compute factual grounding / faithfulness of generated answer against retrieved context."""
    guardrail = GroundingGuardrail()
    res = await guardrail.check(
        text=actual_answer,
        context={"retrieved_chunks": retrieved_chunks}
    )
    score = res.metadata.get("grounding_score", 1.0 if res.passed else 0.0)
    return round(float(score), 4)


def compute_answer_relevance(question: str, actual_answer: str) -> float:
    """Compute keyword overlap relevance between question and answer."""
    if not question or not actual_answer:
        return 0.0
    q_tokens = _tokenize(question)
    a_tokens = _tokenize(actual_answer)
    if not q_tokens:
        return 1.0
    overlap = q_tokens.intersection(a_tokens)
    return round(min(len(overlap) / max(len(q_tokens), 1), 1.0), 4)
