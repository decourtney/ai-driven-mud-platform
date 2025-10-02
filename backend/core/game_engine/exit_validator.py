import re
from difflib import SequenceMatcher
from typing import Optional, List
from backend.core.scenes.scene_models import Exit


class ExitValidator:
    """Utility for matching a target location string against a list of scene exits."""

    STOPWORDS = {"to", "the", "a", "an", "run", "walk", "go", "move", "goto"}

    def __init__(self, similarity_threshold: float = 0.35):
        self.similarity_threshold = similarity_threshold

    def validate(self, target: str, exits: List[Exit]) -> str:
        """
        Match a parsed target against available exits.
        Returns the exit ID string or 'none' if no match meets the threshold.
        """
        if not target or not exits:
            return None

        target = target.strip().lower()

        # Direct ID match
        for e in exits:
            if target == e.id.lower():
                return e.id

        # Best fuzzy match across ID and label
        best_match: Optional[Exit] = None
        best_score = 0.0

        for e in exits:
            score = max(
                self.token_similarity(target, e.id),
                self.token_similarity(target, e.label),
                self.sequence_similarity(target, e.id),
                self.sequence_similarity(target, e.label),
            )
            if score > best_score:
                best_score, best_match = score, e

        return (
            best_match.id
            if best_match and best_score >= self.similarity_threshold
            else None
        )

    def normalize_string(self, text: str) -> List[str]:
        text = re.sub(r"[^\w\s]", "", text.lower())
        return [w for w in text.split() if w not in self.STOPWORDS]

    def token_similarity(self, a: str, b: str) -> float:
        set_a = set(self.normalize_string(a))
        set_b = set(self.normalize_string(b))
        return len(set_a & set_b) / len(set_a | set_b) if set_a or set_b else 0.0

    def sequence_similarity(self, a: str, b: str) -> float:
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()
