import re
from difflib import SequenceMatcher
from typing import Optional, List, Dict
from backend.core.scenes.scene_models import Exit


class ActionValidator:
    """Utility for matching a target location string against a list of scene exits."""

    STOPWORDS = {"to", "the", "a", "an", "run", "walk", "go", "move", "goto"}

    def __init__(self, similarity_threshold: float = 0.35):
        self.similarity_threshold = similarity_threshold

    def validate(self, target: str, matches: List[Dict[str, str]]) -> Dict[str, str]:
        """
        Match a parsed target against available exits.
        Returns the exit ID string or 'none' if no match meets the threshold.
        """
        if not target or not matches:
            return None

        target = target.strip().lower()

        # Direct ID match
        for m in matches:
            if target == m.name.lower():
                return m.name

        # Best fuzzy match across ID and label
        best_match: Optional[Dict[str, str]] = None
        best_score = 0.0

        for m in matches:
            score = max(
                self.token_similarity(target, m.name.replace("_", " ")),
                self.token_similarity(target, m.label),
                self.sequence_similarity(target, m.name.replace("_", " ")),
                self.sequence_similarity(target, m.label),
            )
            print("\033[94m[VALIDATOR]\033[0m Score:", score, "Match:", m.name)
            if score > best_score:
                best_score, best_match = score, m

        return (
            best_match
            if best_match and best_score >= self.similarity_threshold
            else None
        )

    def normalize_string(self, text: str) -> List[str]:
        text = re.sub(r"[^\w\s]", "", text.lower())
        return [w for w in text.split() if w not in self.STOPWORDS]

    def token_similarity(self, a: str, b: str) -> float:
        set_a = set(self.normalize_string(a))
        set_b = set(self.normalize_string(b))
        ts = len(set_a & set_b) / len(set_a | set_b) if set_a or set_b else 0.0
        print(ts)
        return ts

    def sequence_similarity(self, a: str, b: str) -> float:
        sm = SequenceMatcher(None, a.lower(), b.lower()).ratio()
        print(sm)
        return sm
