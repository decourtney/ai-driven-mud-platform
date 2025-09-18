-- DropForeignKey
ALTER TABLE "ChatMessage" DROP CONSTRAINT "ChatMessage_player_id_fkey";

-- AlterTable
ALTER TABLE "ChatMessage" ALTER COLUMN "player_id" DROP NOT NULL;

-- AddForeignKey
ALTER TABLE "ChatMessage" ADD CONSTRAINT "ChatMessage_player_id_fkey" FOREIGN KEY ("player_id") REFERENCES "PlayerState"("id") ON DELETE SET NULL ON UPDATE CASCADE;
