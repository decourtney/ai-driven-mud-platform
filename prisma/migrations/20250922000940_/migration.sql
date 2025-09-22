/*
  Warnings:

  - You are about to drop the column `current_turn_character` on the `GameState` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE "GameState" DROP COLUMN "current_turn_character",
ADD COLUMN     "current_actor" TEXT,
ADD COLUMN     "current_turn_phase" TEXT,
ADD COLUMN     "player_input_locked" BOOLEAN NOT NULL DEFAULT true;
