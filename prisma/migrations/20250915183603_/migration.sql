/*
  Warnings:

  - A unique constraint covering the columns `[game_session_id]` on the table `GameState` will be added. If there are existing duplicate values, this will fail.

*/
-- DropForeignKey
ALTER TABLE "GameState" DROP CONSTRAINT "GameState_game_session_id_fkey";

-- CreateIndex
CREATE UNIQUE INDEX "GameState_game_session_id_key" ON "GameState"("game_session_id");

-- AddForeignKey
ALTER TABLE "GameState" ADD CONSTRAINT "GameState_game_session_id_fkey" FOREIGN KEY ("game_session_id") REFERENCES "GameSession"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
