import re
from difflib import SequenceMatcher
from typing import Optional, List, Dict, Any
from backend.core.scenes.scene_models import Exit
from backend.services.api.models.scene_models import SceneExitRequest
from backend.services.api.models.action_models import TargetValidationRequest
from backend.services.ai_models.model_client import AsyncModelServiceClient
from backend.core.characters.npc_character import NpcCharacter


class ActionValidator:
    """Utility for matching a target location string against a list of scene exits."""

    STOPWORDS = {"to", "the", "a", "an", "run", "walk", "go", "move", "goto"}

    def __init__(self, similarity_threshold: float = 0.60):
        self.similarity_threshold = similarity_threshold

    def validate(self, target: str, matches: List[Dict[str, Any]]) -> Dict[str, Any]:
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
        best_match: Optional[Dict[str, Any]] = None
        best_score = 0.0

        for m in matches:
            score = self.token_similarity(target, m.name.replace("_", " "))

            # score = max(
            #     self.token_similarity(target, m.name.replace("_", " ")),
            #     # self.token_similarity(target, m.label),
            #     # self.sequence_similarity(target, m.name.replace("_", " ")),
            #     # self.sequence_similarity(target, m.label),
            # )
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

    async def llm_validate(
        self,
        target: str,
        npcs: List[NpcCharacter],
        model_client: AsyncModelServiceClient,
    ) -> Dict[str, Any]:
        matches: List[Dict[str, Any]] = [npc.model_dump(mode="json") for npc in npcs]

        try:
            target_validation_request = TargetValidationRequest(
                query=target, candidates=matches
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
        result = await model_client.determine_valid_target(
            target_validation_request
        )
        print(
            "\033[91m[DEBUG]\033[0m Target Validation Result:", result
        )

        return result
