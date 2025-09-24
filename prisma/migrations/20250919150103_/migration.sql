/*
  Warnings:

  - The `current_scene` column on the `GameState` table would be dropped and recreated. This will lead to data loss if there is data in the column.

*/
-- AlterTable
ALTER TABLE "GameState" DROP COLUMN "current_scene",
ADD COLUMN     "current_scene" JSONB,
ALTER COLUMN "current_zone" DROP NOT NULL;
