from typing import Dict
from backend.core.characters.player_character import PlayerCharacter
from backend.core.quests.quest_models import QuestStatus, QuestDefinition, QuestState


class QuestSystem:
    def __init__(self, quest_db: Dict[str, QuestDefinition]):
        self.quest_db = quest_db  # all available quests

    def start_quest(self, pc, quest_id: str):
        if quest_id not in self.quest_db:
            raise ValueError(f"Quest {quest_id} not found")

        pc.active_quests[quest_id] = QuestState(
            quest_id=quest_id, status=QuestStatus.IN_PROGRESS
        )

    def complete_objective(self, pc, quest_id: str, obj_index: int):
        state = pc.active_quests.get(quest_id)
        if not state or state.status != QuestStatus.IN_PROGRESS:
            return

        if obj_index not in state.completed_objectives:
            state.completed_objectives.append(obj_index)

        quest = self.quest_db[quest_id]
        if len(state.completed_objectives) == len(quest.objectives):
            state.status = QuestStatus.COMPLETED

    def grant_rewards(self, pc, quest_id: str, item_db: dict):
        state = pc.active_quests.get(quest_id)
        if not state or state.status != QuestStatus.COMPLETED:
            return

        quest = self.quest_db[quest_id]
        rewards = quest.rewards

        pc.gold += rewards.gold
        pc.xp += rewards.xp

        for item_id in rewards.item_ids:
            if item_id in item_db:
                pc.inventory.add(item_db[item_id])

        # mark quest as finished to prevent re-claiming
        state.status = QuestStatus.FAILED  # or add another "REWARDED" status
