/*
  Warnings:

  - You are about to drop the column `scene_id` on the `SceneDiff` table. All the data in the column will be lost.
  - Added the required column `scene_name` to the `SceneDiff` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "SceneDiff" DROP COLUMN "scene_id",
ADD COLUMN     "scene_name" TEXT NOT NULL;
