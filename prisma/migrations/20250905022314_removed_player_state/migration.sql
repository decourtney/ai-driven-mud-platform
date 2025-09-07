/*
  Warnings:

  - You are about to drop the column `player_state` on the `GameSession` table. All the data in the column will be lost.
  - You are about to drop the column `turn_counter` on the `GameSession` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE "GameSession" DROP COLUMN "player_state",
DROP COLUMN "turn_counter";
