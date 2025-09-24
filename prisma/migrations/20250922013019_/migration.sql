/*
  Warnings:

  - You are about to drop the column `player_input_locked` on the `GameState` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE "GameState" DROP COLUMN "player_input_locked",
ADD COLUMN     "is_player_input_locked" BOOLEAN NOT NULL DEFAULT true;
