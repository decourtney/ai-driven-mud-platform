"use client";

import CharacterPanel from "@/app/components/games/mudai/CharacterPanel";
import ChatPanel from "./ChatPanel";
import { useGameWebSocket } from "@/app/hooks/useGameWebSocket";
import { useState, useEffect } from "react";
import { toast } from "sonner";
import { PlayerCharacter } from "@/app/types/game";

interface GamePageProps {
  slug: string;
  id: string; // This is your session_id
}

export default function GamePage({ slug, id }: GamePageProps) {
  const [activeTab, setActiveTab] = useState<"character" | "chat">("character");

  // Use the WebSocket hook - no more localStorage or REST calls needed!
  const {
    isConnected,
    sendAction,
    chatHistory,
    gameState,
    playerCharacter,
    lastError,
    reconnect,
  } = useGameWebSocket({
    slug,
    sessionId: id,
    onError: (error) => {
      console.error("WebSocket error:", error);
      toast.error(error);
    },
    onConnectionChange: (connected) => {
      if (connected) {
        toast.success("Connected to game server");
      } else {
        toast.error("Disconnected from game server");
      }
    },
    onMessage: (message) => {
      // Handle any custom message processing here
      console.log("Received message:", message);
    },
  });

  // Handle WebSocket errors
  useEffect(() => {
    if (lastError) {
      toast.error(lastError);
    }
  }, [lastError]);

  // console.log("[DEBUG]GameState on GamePage:", gameState);
  // console.log("[DEBUG]PlayerState on GamePage:", playerState);

  // Show loading until we have game state
  if (!gameState || !isConnected) {
    return (
      <div className="flex items-center justify-center flex-1 text-white">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 mx-auto border-b-2 border-green-500 mb-4"></div>
          <p className="text-green-400 font-mono">
            {!isConnected
              ? "Connecting to game server..."
              : "Loading game state..."}
          </p>
          {lastError && (
            <div className="mt-4">
              <p className="text-red-400 font-mono mb-2">Connection Error:</p>
              <p className="text-gray-300 text-sm mb-4">{lastError}</p>
              <button
                onClick={reconnect}
                className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded font-mono"
              >
                Retry Connection
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  const handlePlayerAction = (action: string) => {
    console.log("Sending action via WebSocket:", action);
    sendAction(action);
  };

  return (
    <div className="flex flex-col md:flex-row flex-1 min-h-0 text-white">
      {/* Mobile Tabs */}
      <div className="md:hidden flex border-b border-green-500">
        <button
          className={`flex-1 p-2 ${
            activeTab === "character" ? "bg-gray-800" : "bg-gray-900"
          }`}
          onClick={() => setActiveTab("character")}
        >
          Character
        </button>
        <button
          className={`flex-1 p-2 ${
            activeTab === "chat" ? "bg-gray-800" : "bg-gray-900"
          }`}
          onClick={() => setActiveTab("chat")}
        >
          Chat
        </button>
      </div>

      {/* Character Panel */}
      <div
        className={`flex flex-1 md:flex-initial md:w-150 ${
          activeTab !== "character" ? "hidden md:flex" : ""
        }`}
      >
        <CharacterPanel playerCharacter={playerCharacter} />
      </div>

      {/* Chat Interface */}
      <div
        className={`flex flex-1 min-h-0 ${
          activeTab !== "chat" ? "hidden md:flex" : ""
        }`}
      >
        <ChatPanel
          onPlayerAction={handlePlayerAction}
          chatHistory={chatHistory}
          isConnected={isConnected}
          slug={slug}
          gameState={gameState}
        />
      </div>
    </div>
  );
}
