"""Fit existing narration by removing whole middle sentences, never audio tails."""
import re


def fit_complete_sentences(text: str, minimum: int, maximum: int) -> str | None:
    if not 0 < minimum <= maximum:
        raise ValueError("Invalid word window")
    sentences = re.split(r"(?<=[.!؟؛])\s+", text.strip())
    if any(not re.search(r"[.!؟؛:]$", sentence) for sentence in sentences):
        return None
    while len(" ".join(sentences).split()) > maximum and len(sentences) > 2:
        # Preserve the opening, the core explanation immediately after it,
        # and the conclusion; drop later middle details before earlier ones.
        del sentences[-2]
    result = " ".join(sentences)
    return result if minimum <= len(result.split()) <= maximum else None
