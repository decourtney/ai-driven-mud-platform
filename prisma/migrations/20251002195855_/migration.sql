/*
  Warnings:

  - You are about to drop the column `creatureType` on the `BaseCharacter` table. All the data in the column will be lost.
  - You are about to drop the column `gameSessionId` on the `PlayerCharacter` table. All the data in the column will be lost.
  - Added the required column `creature_type` to the `BaseCharacter` table without a default value. This is not possible if the table is not empty.

*/
-- DropForeignKey
ALTER TABLE "PlayerCharacter" DROP CONSTRAINT "PlayerCharacter_gameSessionId_fkey";

-- AlterTable
ALTER TABLE "BaseCharacter" DROP COLUMN "creatureType",
ADD COLUMN     "creature_type" "CreatureType" NOT NULL;

-- AlterTable
ALTER TABLE "PlayerCharacter" DROP COLUMN "gameSessionId",
ADD COLUMN     "game_session_id" TEXT;

-- AddForeignKey
ALTER TABLE "PlayerCharacter" ADD CONSTRAINT "PlayerCharacter_game_session_id_fkey" FOREIGN KEY ("game_session_id") REFERENCES "GameSession"("id") ON DELETE SET NULL ON UPDATE CASCADE;
