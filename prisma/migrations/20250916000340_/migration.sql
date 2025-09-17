-- DropForeignKey
ALTER TABLE "GameState" DROP CONSTRAINT "GameState_game_session_id_fkey";

-- AddForeignKey
ALTER TABLE "GameState" ADD CONSTRAINT "GameState_game_session_id_fkey" FOREIGN KEY ("game_session_id") REFERENCES "GameSession"("id") ON DELETE CASCADE ON UPDATE CASCADE;
