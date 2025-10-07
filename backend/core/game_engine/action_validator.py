import Levenshtein, re
from collections import Counter
from difflib import SequenceMatcher
from typing import Optional, List, Dict, Any
from backend.core.scenes.scene_models import Exit
from backend.services.api.models.scene_models import SceneExitRequest
from backend.services.api.models.action_models import TargetValidationRequest
from backend.services.ai_models.model_client import AsyncModelServiceClient
from backend.core.characters.npc_character import NpcCharacter
from backend.core.characters.base_character import BaseCharacter


class ActionValidator:
    """Utility for matching a target location string against a list of scene exits."""

    STOPWORDS = {"to", "the", "a", "an", "run", "walk", "go", "move", "goto"}

    def __init__(self, similarity_threshold: float = 0.60):
        self.similarity_threshold = similarity_threshold

    def validate(self, query: str, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Match a parsed target against available exits.
        Returns the exit ID string or 'none' if no match meets the threshold.
        """
        if not query or not candidates:
            return None

        query = query.strip().lower()
        print("\n\033[95m[INPUT]\033[0m", query)

        # Direct ID match
        for m in candidates:
            if query == m.name.lower():
                return m.name

        # Best fuzzy match across ID and label
        best_match: Optional[Dict[str, Any]] = None
        best_score = 0.0

        for m in candidates:
            score = self.token_similarity(query, m.name.replace("_", " "))
            # print("\n\033[95m[TARGET]\033[0m", m.name.replace("_", " "))
            # score = max(
            #     self.token_similarity(query, m.name.replace("_", " ")),
            #     self.sequence_similarity(query, m.name.replace("_", " ")),
            #     self.levenshtein_similarity(query, m.name.replace("_", " ")),
            # )
            print("\033[92m[VALIDATOR]\033[0m Score:", score, "Match:", m.name, '\n')

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
        tokens_a = self.normalize_string(a)
        tokens_b = self.normalize_string(b)
        counter_a = Counter(tokens_a)
        counter_b = Counter(tokens_b)
        ts = (
            sum(min(counter_a[t], counter_b[t]) for t in set(tokens_a) | set(tokens_b))
            / sum(
                max(counter_a[t], counter_b[t]) for t in set(tokens_a) | set(tokens_b)
            )
            if tokens_a or tokens_b
            else 0.0
        )
        print("\033[94m[Jaccard]\033[0m:", round(ts, 2))
        return ts

    def sequence_similarity(self, a: str, b: str) -> float:
        sm = SequenceMatcher(None, a.lower(), b.lower()).ratio()
        print("\033[94m[SequenceMatcher]\033[0m:", round(sm, 2))
        return sm

    def levenshtein_similarity(self, a: str, b: str) -> float:
        ls = Levenshtein.ratio(a.lower(), b.lower())
        print("\033[94m[Levenshtein]\033[0m:", round(ls, 2))
        return ls

    async def llm_validate(
        self,
        query: str,
        candidates: List[BaseCharacter],
        model_client: AsyncModelServiceClient,
    ) -> Dict[str, Any]:
        candidates: List[Dict[str, Any]] = [
            c.model_dump(mode="json") for c in candidates
        ]

        try:
            target_validation_request = TargetValidationRequest(
                query=query, candidates=candidates
            )
        except Exception as e:
            import traceback

            print("\033[91m[ERROR]\033[0m Failed to build TargetValidationRequest:")
            traceback.print_exc()
            return {}

        # print(
        #     "\033[91m[DEBUG]\033[0m Target Validation Request:",
        #     target_validation_request,
        # )
        result = await model_client.determine_valid_target(target_validation_request)

        return result
