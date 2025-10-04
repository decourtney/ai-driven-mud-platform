-- DropForeignKey
ALTER TABLE "AbilityOnCharacter" DROP CONSTRAINT "AbilityOnCharacter_ability_id_fkey";

-- DropForeignKey
ALTER TABLE "AbilityOnCharacter" DROP CONSTRAINT "AbilityOnCharacter_character_id_fkey";

-- DropForeignKey
ALTER TABLE "ConditionEffectInstance" DROP CONSTRAINT "ConditionEffectInstance_character_id_fkey";

-- DropForeignKey
ALTER TABLE "Inventory" DROP CONSTRAINT "Inventory_character_id_fkey";

-- DropForeignKey
ALTER TABLE "Inventory" DROP CONSTRAINT "Inventory_item_id_fkey";

-- DropForeignKey
ALTER TABLE "LootEntry" DROP CONSTRAINT "LootEntry_item_id_fkey";

-- DropForeignKey
ALTER TABLE "LootEntry" DROP CONSTRAINT "LootEntry_npc_id_fkey";

-- DropForeignKey
ALTER TABLE "NpcCharacter" DROP CONSTRAINT "NpcCharacter_base_id_fkey";

-- DropForeignKey
ALTER TABLE "PlayerCharacter" DROP CONSTRAINT "PlayerCharacter_base_id_fkey";

-- DropForeignKey
ALTER TABLE "QuestObjective" DROP CONSTRAINT "QuestObjective_quest_def_id_fkey";

-- DropForeignKey
ALTER TABLE "QuestReward" DROP CONSTRAINT "QuestReward_quest_def_id_fkey";

-- DropForeignKey
ALTER TABLE "QuestState" DROP CONSTRAINT "QuestState_player_id_fkey";

-- DropForeignKey
ALTER TABLE "QuestState" DROP CONSTRAINT "QuestState_quest_id_fkey";

-- DropForeignKey
ALTER TABLE "SpellOnCharacter" DROP CONSTRAINT "SpellOnCharacter_character_id_fkey";

-- DropForeignKey
ALTER TABLE "SpellOnCharacter" DROP CONSTRAINT "SpellOnCharacter_spell_id_fkey";

-- DropForeignKey
ALTER TABLE "SpellSlot" DROP CONSTRAINT "SpellSlot_player_id_fkey";

-- AlterTable
ALTER TABLE "BaseCharacter" ADD COLUMN     "game_session_id" TEXT;

-- AddForeignKey
ALTER TABLE "BaseCharacter" ADD CONSTRAINT "BaseCharacter_game_session_id_fkey" FOREIGN KEY ("game_session_id") REFERENCES "GameSession"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "PlayerCharacter" ADD CONSTRAINT "PlayerCharacter_base_id_fkey" FOREIGN KEY ("base_id") REFERENCES "BaseCharacter"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "NpcCharacter" ADD CONSTRAINT "NpcCharacter_base_id_fkey" FOREIGN KEY ("base_id") REFERENCES "BaseCharacter"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "AbilityOnCharacter" ADD CONSTRAINT "AbilityOnCharacter_ability_id_fkey" FOREIGN KEY ("ability_id") REFERENCES "Ability"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "AbilityOnCharacter" ADD CONSTRAINT "AbilityOnCharacter_character_id_fkey" FOREIGN KEY ("character_id") REFERENCES "BaseCharacter"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "SpellSlot" ADD CONSTRAINT "SpellSlot_player_id_fkey" FOREIGN KEY ("player_id") REFERENCES "PlayerCharacter"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "SpellOnCharacter" ADD CONSTRAINT "SpellOnCharacter_spell_id_fkey" FOREIGN KEY ("spell_id") REFERENCES "Spell"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "SpellOnCharacter" ADD CONSTRAINT "SpellOnCharacter_character_id_fkey" FOREIGN KEY ("character_id") REFERENCES "BaseCharacter"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Inventory" ADD CONSTRAINT "Inventory_item_id_fkey" FOREIGN KEY ("item_id") REFERENCES "Item"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Inventory" ADD CONSTRAINT "Inventory_character_id_fkey" FOREIGN KEY ("character_id") REFERENCES "BaseCharacter"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "LootEntry" ADD CONSTRAINT "LootEntry_item_id_fkey" FOREIGN KEY ("item_id") REFERENCES "Item"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "LootEntry" ADD CONSTRAINT "LootEntry_npc_id_fkey" FOREIGN KEY ("npc_id") REFERENCES "NpcCharacter"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ConditionEffectInstance" ADD CONSTRAINT "ConditionEffectInstance_character_id_fkey" FOREIGN KEY ("character_id") REFERENCES "BaseCharacter"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "QuestState" ADD CONSTRAINT "QuestState_quest_id_fkey" FOREIGN KEY ("quest_id") REFERENCES "QuestDefinition"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "QuestState" ADD CONSTRAINT "QuestState_player_id_fkey" FOREIGN KEY ("player_id") REFERENCES "PlayerCharacter"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "QuestObjective" ADD CONSTRAINT "QuestObjective_quest_def_id_fkey" FOREIGN KEY ("quest_def_id") REFERENCES "QuestDefinition"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "QuestReward" ADD CONSTRAINT "QuestReward_quest_def_id_fkey" FOREIGN KEY ("quest_def_id") REFERENCES "QuestDefinition"("id") ON DELETE CASCADE ON UPDATE CASCADE;
