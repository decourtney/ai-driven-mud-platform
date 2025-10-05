/*
  Warnings:

  - Added the required column `label` to the `NpcCharacter` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "NpcCharacter" ADD COLUMN     "label" TEXT NOT NULL;
