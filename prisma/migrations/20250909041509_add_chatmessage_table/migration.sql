-- CreateEnum
CREATE TYPE "SpeakerType" AS ENUM ('player', 'narrator');

-- CreateEnum
CREATE TYPE "ActionType" AS ENUM ('attack', 'spell', 'social', 'interact', 'movement', 'user_prompt', 'narrate');

-- CreateTable
CREATE TABLE "ChatMessage" (
    "id" TEXT NOT NULL,
    "session_id" TEXT NOT NULL,
    "speaker" "SpeakerType" NOT NULL,
    "action" "ActionType" NOT NULL,
    "content" TEXT NOT NULL,
    "timestamp" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ChatMessage_pkey" PRIMARY KEY ("id")
);

-- AddForeignKey
ALTER TABLE "ChatMessage" ADD CONSTRAINT "ChatMessage_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "GameSession"("id") ON DELETE CASCADE ON UPDATE CASCADE;
