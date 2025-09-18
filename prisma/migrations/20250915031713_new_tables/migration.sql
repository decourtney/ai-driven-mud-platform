/*
  Warnings:

  - You are about to drop the column `timestamp` on the `ChatMessage` table. All the data in the column will be lost.
  - You are about to drop the column `game_state` on the `GameSession` table. All the data in the column will be lost.
  - You are about to drop the column `slug` on the `GameSession` table. All the data in the column will be lost.
  - Added the required column `player_id` to the `ChatMessage` table without a default value. This is not possible if the table is not empty.
  - Added the required column `updated_at` to the `ChatMessage` table without a default value. This is not possible if the table is not empty.
  - Added the required column `game_id` to the `GameSession` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "ChatMessage" DROP COLUMN "timestamp",
ADD COLUMN     "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN     "player_id" TEXT NOT NULL,
ADD COLUMN     "updated_at" TIMESTAMP(3) NOT NULL;

-- AlterTable
ALTER TABLE "GameSession" DROP COLUMN "game_state",
DROP COLUMN "slug",
ADD COLUMN     "game_id" TEXT NOT NULL;

-- CreateTable
CREATE TABLE "GameState" (
    "id" TEXT NOT NULL,
    "game_session_id" TEXT NOT NULL,
    "weather" TEXT,
    "in_combat" BOOLEAN NOT NULL DEFAULT false,
    "objectives" JSONB,
    "story_beats" JSONB,
    "time_of_day" TEXT,
    "last_updated" TIMESTAMP(3) NOT NULL,
    "save_version" TEXT,
    "turn_counter" INTEGER,
    "current_scene" JSONB,
    "loaded_scenes" JSONB,
    "recent_events" JSONB,
    "session_started" TIMESTAMP(3),
    "initiative_order" JSONB,
    "items_discovered" JSONB,
    "location_history" JSONB,
    "important_npcs_met" JSONB,
    "completed_objectives" JSONB,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "GameState_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "PlayerState" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "game_session_id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "bio" TEXT,
    "gold" INTEGER NOT NULL DEFAULT 0,
    "level" INTEGER NOT NULL DEFAULT 1,
    "max_hp" INTEGER NOT NULL,
    "current_hp" INTEGER NOT NULL,
    "max_mp" INTEGER NOT NULL,
    "current_mp" INTEGER NOT NULL,
    "strength" INTEGER NOT NULL,
    "dexterity" INTEGER NOT NULL,
    "constitution" INTEGER NOT NULL,
    "intelligence" INTEGER NOT NULL,
    "wisdom" INTEGER NOT NULL,
    "charisma" INTEGER NOT NULL,
    "armor_class" INTEGER NOT NULL,
    "can_act" BOOLEAN NOT NULL DEFAULT true,
    "is_alive" BOOLEAN NOT NULL DEFAULT true,
    "temporary_hp" INTEGER NOT NULL DEFAULT 0,
    "character_type" TEXT NOT NULL,
    "equipped_armor" JSONB,
    "equipped_weapon" JSONB,
    "inventory" JSONB,
    "status_effects" JSONB,
    "location" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "PlayerState_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "SceneDiff" (
    "id" TEXT NOT NULL,
    "game_session_id" TEXT NOT NULL,
    "zone" TEXT NOT NULL,
    "scene" TEXT NOT NULL,
    "diff" JSONB,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "SceneDiff_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "NpcState" (
    "id" TEXT NOT NULL,
    "scene_state_id" TEXT NOT NULL,
    "npc_id" TEXT NOT NULL,
    "name" TEXT,
    "type" TEXT NOT NULL,
    "is_alive" BOOLEAN NOT NULL DEFAULT true,
    "current_hp" INTEGER,
    "max_hp" INTEGER,
    "ai_state" JSONB,
    "inventory" JSONB,
    "dialogue_state" JSONB,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "NpcState_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "PlayerState_user_id_key" ON "PlayerState"("user_id");

-- AddForeignKey
ALTER TABLE "GameState" ADD CONSTRAINT "GameState_game_session_id_fkey" FOREIGN KEY ("game_session_id") REFERENCES "GameSession"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "PlayerState" ADD CONSTRAINT "PlayerState_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "PlayerState" ADD CONSTRAINT "PlayerState_game_session_id_fkey" FOREIGN KEY ("game_session_id") REFERENCES "GameSession"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "SceneDiff" ADD CONSTRAINT "SceneDiff_game_session_id_fkey" FOREIGN KEY ("game_session_id") REFERENCES "GameSession"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "NpcState" ADD CONSTRAINT "NpcState_scene_state_id_fkey" FOREIGN KEY ("scene_state_id") REFERENCES "SceneDiff"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ChatMessage" ADD CONSTRAINT "ChatMessage_player_id_fkey" FOREIGN KEY ("player_id") REFERENCES "PlayerState"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
