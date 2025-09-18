/*
  Warnings:

  - You are about to drop the column `last_updated` on the `GameState` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE "GameState" DROP COLUMN "last_updated",
ADD COLUMN     "current_turn_character" INTEGER;
