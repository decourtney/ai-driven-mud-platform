/*
  Warnings:

  - The values [attack,spell,social,interact,movement,user_prompt,narrate] on the enum `ActionType` will be removed. If these variants are still used in the database, this will fail.
  - The values [player,narrator,system,error] on the enum `SpeakerType` will be removed. If these variants are still used in the database, this will fail.
  - You are about to drop the column `session_id` on the `ChatMessage` table. All the data in the column will be lost.
  - You are about to drop the column `diff` on the `SceneDiff` table. All the data in the column will be lost.
  - You are about to drop the column `scene` on the `SceneDiff` table. All the data in the column will be lost.
  - You are about to drop the `NpcState` table. If the table is not empty, all the data it contains will be lost.
  - You are about to drop the `PlayerState` table. If the table is not empty, all the data it contains will be lost.
  - Added the required column `game_session_id` to the `ChatMessage` table without a default value. This is not possible if the table is not empty.
  - Added the required column `scene_id` to the `SceneDiff` table without a default value. This is not possible if the table is not empty.

*/
-- CreateEnum
CREATE TYPE "QuestStatus" AS ENUM ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'FAILED');

-- CreateEnum
CREATE TYPE "AbilityEffectType" AS ENUM ('DAMAGE', 'HEAL', 'BUFF', 'DEBUFF', 'CONTROL', 'UTILITY');

-- CreateEnum
CREATE TYPE "CharacterType" AS ENUM ('PLAYER', 'NPC');

-- CreateEnum
CREATE TYPE "CreatureType" AS ENUM ('ABERRATION', 'BEAST', 'CELESTIAL', 'CONSTRUCT', 'DRAGON', 'ELEMENTAL', 'FIEND', 'GIANT', 'HUMANOID', 'MONSTROSITY', 'OOZE', 'PLANT', 'UNDEAD', 'OTHER');

-- CreateEnum
CREATE TYPE "Disposition" AS ENUM ('FRIENDLY', 'NEUTRAL', 'AGGRESSIVE');

-- CreateEnum
CREATE TYPE "EquipSlot" AS ENUM ('HEAD', 'CHEST', 'LEGS', 'FEET', 'HANDS', 'WEAPON', 'SHIELD', 'ACCESSORY');

-- CreateEnum
CREATE TYPE "SpellSchool" AS ENUM ('ABJURATION', 'CONJURATION', 'DIVINATION', 'ENCHANTMENT', 'EVOCATION', 'ILLUSION', 'NECROMANCY', 'TRANSMUTATION');

-- CreateEnum
CREATE TYPE "ConditionEffect" AS ENUM ('BLEEDING', 'BLINDING', 'CHARMED', 'DEAFENED', 'FRIGHTENED', 'GRAPPLED', 'INCAPACITATED', 'INVISIBLE', 'PARALYZED', 'PETRIFIED', 'POISONED', 'PRONE', 'RESTRAINED', 'SILENCED', 'STUNNED', 'UNCONSCIOUS', 'EXHAUSTION');

-- CreateEnum
CREATE TYPE "AbilityType" AS ENUM ('MELEE', 'RANGED', 'SPECIAL');

-- AlterEnum
BEGIN;
CREATE TYPE "ActionType_new" AS ENUM ('ATTACK', 'SPELL', 'SOCIAL', 'INTERACT', 'MOVEMENT', 'USER_PROMPT', 'NARRATE');
ALTER TABLE "ChatMessage" ALTER COLUMN "action" TYPE "ActionType_new" USING ("action"::text::"ActionType_new");
ALTER TYPE "ActionType" RENAME TO "ActionType_old";
ALTER TYPE "ActionType_new" RENAME TO "ActionType";
DROP TYPE "ActionType_old";
COMMIT;

-- AlterEnum
BEGIN;
CREATE TYPE "SpeakerType_new" AS ENUM ('PLAYER', 'NARRATOR', 'SYSTEM', 'ERROR');
ALTER TABLE "ChatMessage" ALTER COLUMN "speaker" TYPE "SpeakerType_new" USING ("speaker"::text::"SpeakerType_new");
ALTER TYPE "SpeakerType" RENAME TO "SpeakerType_old";
ALTER TYPE "SpeakerType_new" RENAME TO "SpeakerType";
DROP TYPE "SpeakerType_old";
COMMIT;

-- DropForeignKey
ALTER TABLE "ChatMessage" DROP CONSTRAINT "ChatMessage_player_id_fkey";

-- DropForeignKey
ALTER TABLE "ChatMessage" DROP CONSTRAINT "ChatMessage_session_id_fkey";

-- DropForeignKey
ALTER TABLE "NpcState" DROP CONSTRAINT "NpcState_scene_state_id_fkey";

-- DropForeignKey
ALTER TABLE "PlayerState" DROP CONSTRAINT "PlayerState_game_session_id_fkey";

-- DropForeignKey
ALTER TABLE "PlayerState" DROP CONSTRAINT "PlayerState_user_id_fkey";

-- AlterTable
ALTER TABLE "ChatMessage" DROP COLUMN "session_id",
ADD COLUMN     "game_session_id" TEXT NOT NULL;

-- AlterTable
ALTER TABLE "SceneDiff" DROP COLUMN "diff",
DROP COLUMN "scene",
ADD COLUMN     "changes" JSONB,
ADD COLUMN     "scene_id" TEXT NOT NULL;

-- DropTable
DROP TABLE "NpcState";

-- DropTable
DROP TABLE "PlayerState";

-- CreateTable
CREATE TABLE "BaseCharacter" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "bio" TEXT,
    "character_type" "CharacterType" NOT NULL,
    "creatureType" "CreatureType" NOT NULL,

    CONSTRAINT "BaseCharacter_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "PlayerCharacter" (
    "id" TEXT NOT NULL,
    "base_id" TEXT NOT NULL,
    "level" INTEGER NOT NULL,
    "max_hp" INTEGER NOT NULL,
    "current_hp" INTEGER NOT NULL,
    "temporary_hp" INTEGER NOT NULL,
    "armor_class" INTEGER NOT NULL,
    "initiative" INTEGER NOT NULL,
    "initiative_bonus" INTEGER NOT NULL,
    "strength" INTEGER NOT NULL,
    "dexterity" INTEGER NOT NULL,
    "constitution" INTEGER NOT NULL,
    "intelligence" INTEGER NOT NULL,
    "wisdom" INTEGER NOT NULL,
    "charisma" INTEGER NOT NULL,
    "gold" INTEGER NOT NULL,
    "experience" INTEGER NOT NULL DEFAULT 0,
    "natural_heal" TEXT NOT NULL,
    "current_zone" TEXT NOT NULL,
    "current_scene" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "gameSessionId" TEXT,

    CONSTRAINT "PlayerCharacter_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "NpcCharacter" (
    "id" TEXT NOT NULL,
    "base_id" TEXT NOT NULL,
    "level" INTEGER NOT NULL,
    "max_hp" INTEGER NOT NULL,
    "current_hp" INTEGER NOT NULL,
    "temporary_hp" INTEGER NOT NULL,
    "armor_class" INTEGER NOT NULL,
    "initiative" INTEGER NOT NULL,
    "initiative_bonus" INTEGER NOT NULL,
    "strength" INTEGER NOT NULL,
    "dexterity" INTEGER NOT NULL,
    "constitution" INTEGER NOT NULL,
    "intelligence" INTEGER NOT NULL,
    "wisdom" INTEGER NOT NULL,
    "charisma" INTEGER NOT NULL,
    "gold" INTEGER NOT NULL,
    "damage" TEXT NOT NULL,
    "available_quests" TEXT[],
    "disposition" "Disposition" NOT NULL DEFAULT 'NEUTRAL',
    "scene_diff_id" TEXT,

    CONSTRAINT "NpcCharacter_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "AbilityOnCharacter" (
    "id" TEXT NOT NULL,
    "ability_id" TEXT NOT NULL,
    "character_id" TEXT NOT NULL,

    CONSTRAINT "AbilityOnCharacter_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Ability" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "cooldown" INTEGER,
    "damage_dice" INTEGER,
    "ability_type" "AbilityType" NOT NULL,
    "effect_type" "AbilityEffectType",

    CONSTRAINT "Ability_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "SpellSlot" (
    "id" TEXT NOT NULL,
    "level" INTEGER NOT NULL,
    "used" BOOLEAN NOT NULL DEFAULT false,
    "player_id" TEXT NOT NULL,

    CONSTRAINT "SpellSlot_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "SpellOnCharacter" (
    "id" TEXT NOT NULL,
    "spell_id" TEXT NOT NULL,
    "character_id" TEXT NOT NULL,

    CONSTRAINT "SpellOnCharacter_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Spell" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "level" INTEGER NOT NULL,
    "cooldown" INTEGER,
    "range" TEXT,
    "damage_dice" INTEGER,
    "school" "SpellSchool" NOT NULL,

    CONSTRAINT "Spell_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Inventory" (
    "id" TEXT NOT NULL,
    "quantity" INTEGER NOT NULL DEFAULT 1,
    "equipped" BOOLEAN NOT NULL DEFAULT false,
    "slot" "EquipSlot",
    "item_id" TEXT NOT NULL,
    "character_id" TEXT NOT NULL,

    CONSTRAINT "Inventory_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "LootEntry" (
    "id" TEXT NOT NULL,
    "drop_rate" DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    "item_id" TEXT NOT NULL,
    "npc_id" TEXT NOT NULL,

    CONSTRAINT "LootEntry_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "Item" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "base_damage" INTEGER,
    "base_armor" INTEGER,

    CONSTRAINT "Item_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ConditionEffectInstance" (
    "id" TEXT NOT NULL,
    "duration" INTEGER NOT NULL,
    "intensity" INTEGER NOT NULL,
    "source" TEXT,
    "effect" "ConditionEffect" NOT NULL,
    "character_id" TEXT NOT NULL,

    CONSTRAINT "ConditionEffectInstance_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "QuestState" (
    "id" TEXT NOT NULL,
    "objectives" JSONB NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,
    "completed_at" TIMESTAMP(3),
    "status" "QuestStatus" NOT NULL,
    "quest_id" TEXT NOT NULL,
    "player_id" TEXT NOT NULL,

    CONSTRAINT "QuestState_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "QuestObjective" (
    "id" TEXT NOT NULL,
    "description" TEXT NOT NULL,
    "required" INTEGER NOT NULL DEFAULT 1,
    "quest_def_id" TEXT NOT NULL,

    CONSTRAINT "QuestObjective_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "QuestReward" (
    "id" TEXT NOT NULL,
    "gold" INTEGER NOT NULL DEFAULT 0,
    "xp" INTEGER NOT NULL DEFAULT 0,
    "item_ids" TEXT[],
    "quest_def_id" TEXT NOT NULL,

    CONSTRAINT "QuestReward_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "QuestDefinition" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT NOT NULL,
    "level_requirement" INTEGER NOT NULL,
    "quest_type" TEXT NOT NULL,
    "repeatable" BOOLEAN NOT NULL DEFAULT false,
    "prerequisites" TEXT[],

    CONSTRAINT "QuestDefinition_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "PlayerCharacter_base_id_key" ON "PlayerCharacter"("base_id");

-- AddForeignKey
ALTER TABLE "PlayerCharacter" ADD CONSTRAINT "PlayerCharacter_base_id_fkey" FOREIGN KEY ("base_id") REFERENCES "BaseCharacter"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "PlayerCharacter" ADD CONSTRAINT "PlayerCharacter_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "PlayerCharacter" ADD CONSTRAINT "PlayerCharacter_gameSessionId_fkey" FOREIGN KEY ("gameSessionId") REFERENCES "GameSession"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "NpcCharacter" ADD CONSTRAINT "NpcCharacter_base_id_fkey" FOREIGN KEY ("base_id") REFERENCES "BaseCharacter"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "NpcCharacter" ADD CONSTRAINT "NpcCharacter_scene_diff_id_fkey" FOREIGN KEY ("scene_diff_id") REFERENCES "SceneDiff"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "AbilityOnCharacter" ADD CONSTRAINT "AbilityOnCharacter_ability_id_fkey" FOREIGN KEY ("ability_id") REFERENCES "Ability"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "AbilityOnCharacter" ADD CONSTRAINT "AbilityOnCharacter_character_id_fkey" FOREIGN KEY ("character_id") REFERENCES "BaseCharacter"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "SpellSlot" ADD CONSTRAINT "SpellSlot_player_id_fkey" FOREIGN KEY ("player_id") REFERENCES "PlayerCharacter"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "SpellOnCharacter" ADD CONSTRAINT "SpellOnCharacter_spell_id_fkey" FOREIGN KEY ("spell_id") REFERENCES "Spell"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "SpellOnCharacter" ADD CONSTRAINT "SpellOnCharacter_character_id_fkey" FOREIGN KEY ("character_id") REFERENCES "BaseCharacter"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Inventory" ADD CONSTRAINT "Inventory_item_id_fkey" FOREIGN KEY ("item_id") REFERENCES "Item"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "Inventory" ADD CONSTRAINT "Inventory_character_id_fkey" FOREIGN KEY ("character_id") REFERENCES "BaseCharacter"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "LootEntry" ADD CONSTRAINT "LootEntry_item_id_fkey" FOREIGN KEY ("item_id") REFERENCES "Item"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "LootEntry" ADD CONSTRAINT "LootEntry_npc_id_fkey" FOREIGN KEY ("npc_id") REFERENCES "NpcCharacter"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ConditionEffectInstance" ADD CONSTRAINT "ConditionEffectInstance_character_id_fkey" FOREIGN KEY ("character_id") REFERENCES "BaseCharacter"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "QuestState" ADD CONSTRAINT "QuestState_quest_id_fkey" FOREIGN KEY ("quest_id") REFERENCES "QuestDefinition"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "QuestState" ADD CONSTRAINT "QuestState_player_id_fkey" FOREIGN KEY ("player_id") REFERENCES "PlayerCharacter"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "QuestObjective" ADD CONSTRAINT "QuestObjective_quest_def_id_fkey" FOREIGN KEY ("quest_def_id") REFERENCES "QuestDefinition"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "QuestReward" ADD CONSTRAINT "QuestReward_quest_def_id_fkey" FOREIGN KEY ("quest_def_id") REFERENCES "QuestDefinition"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ChatMessage" ADD CONSTRAINT "ChatMessage_player_id_fkey" FOREIGN KEY ("player_id") REFERENCES "PlayerCharacter"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ChatMessage" ADD CONSTRAINT "ChatMessage_game_session_id_fkey" FOREIGN KEY ("game_session_id") REFERENCES "GameSession"("id") ON DELETE CASCADE ON UPDATE CASCADE;
