/*
  Warnings:

  - You are about to drop the column `current_scene` on the `GameState` table. All the data in the column will be lost.
  - You are about to drop the column `current_zone` on the `GameState` table. All the data in the column will be lost.
  - You are about to drop the column `location` on the `PlayerState` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE "GameState" DROP COLUMN "current_scene",
DROP COLUMN "current_zone";

-- AlterTable
ALTER TABLE "PlayerState" DROP COLUMN "location",
ADD COLUMN     "current_scene" TEXT,
ADD COLUMN     "current_zone" TEXT;
