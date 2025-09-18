/*
  Warnings:

  - Added the required column `game_id` to the `GameState` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "GameState" ADD COLUMN     "game_id" TEXT NOT NULL;
