/*
  Warnings:

  - Added the required column `current_zone` to the `GameState` table without a default value. This is not possible if the table is not empty.
  - Made the column `current_scene` on table `GameState` required. This step will fail if there are existing NULL values in that column.

*/
-- AlterTable
ALTER TABLE "GameState" ADD COLUMN     "current_zone" TEXT NOT NULL,
ALTER COLUMN "current_scene" SET NOT NULL,
ALTER COLUMN "current_scene" SET DATA TYPE TEXT;
