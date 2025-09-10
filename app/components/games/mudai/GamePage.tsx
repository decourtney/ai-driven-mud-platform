"use client";

import CharacterPanel from "@/app/components/games/mudai/CharacterPanel";
import ChatPanel from "./ChatPanel";
import { useGameWebSocket } from "@/app/hooks/useGameWebSocket";
import { useState, useEffect } from "react";
import { toast } from "sonner";

interface GamePageProps {
  slug: string;
  id: string; // This is your session_id
}

export default function GamePage({ slug, id }: GamePageProps) {
  const [activeTab, setActiveTab] = useState<"character" | "chat">("character");
  const userId = "user123"; // Get this from your auth system

  // Use the WebSocket hook - no more localStorage or REST calls needed!
  const {
    isConnected,
    sendAction,
    chatHistory,
    gameState,
    lastError,
    reconnect,
  } = useGameWebSocket({
    slug,
    sessionId: id,
    userId,
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

  // Show loading until we have game state
  if (!gameState || !isConnected) {
    return (
      <div className="flex items-center justify-center flex-1 text-white">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-500 mb-4"></div>
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

  // Extract player state from game state
  // Adjust these paths based on your actual game state structure
  const playerState = {
    character_id: gameState.player?.character_id || "",
    name: gameState.player?.name || "Unknown",
    character_type: "player",
    level: gameState.player?.level || 1,
    bio: gameState.player?.bio || "",
    max_hp: gameState.player?.max_hp || 100,
    current_hp: gameState.player?.current_hp || 100,
    temporary_hp: gameState.player?.temporary_hp || 0,
    armor_class: gameState.player?.armor_class || 10,
    strength: gameState.player?.strength || 10,
    dexterity: gameState.player?.dexterity || 10,
    constitution: gameState.player?.constitution || 10,
    intelligence: gameState.player?.intelligence || 10,
    wisdom: gameState.player?.wisdom || 10,
    charisma: gameState.player?.charisma || 10,
    initiative_bonus: gameState.player?.initiative_bonus || 0,
    speed: gameState.player?.speed || 30,
    proficiency_bonus: gameState.player?.proficiency_bonus || 2,
    max_mp: gameState.player?.max_mp || 0,
    current_mp: gameState.player?.current_mp || 0,
    hit_dice: gameState.player?.hit_dice || "1d8",
    equipped_weapon: gameState.player?.equipped_weapon || null,
    equipped_armor: gameState.player?.equipped_armor || null,
    equipped_shield: gameState.player?.equipped_shield || null,
    inventory: gameState.player?.inventory || [],
    gold: gameState.player?.gold || 0,
    known_spells: gameState.player?.known_spells || [],
    spell_slots: gameState.player?.spell_slots || {},
    abilities: gameState.player?.abilities || [],
    status_effects: gameState.player?.status_effects || [],
    is_surprised: gameState.player?.is_surprised || false,
    has_taken_action: gameState.player?.has_taken_action || false,
    has_taken_bonus_action: gameState.player?.has_taken_bonus_action || false,
    has_moved: gameState.player?.has_moved || false,
    movement_used: gameState.player?.movement_used || 0,
    ai_personality: gameState.player?.ai_personality || "",
    ai_priorities: gameState.player?.ai_priorities || [],
    metadata: gameState.player?.metadata || {},
    last_updated: new Date().toISOString(),
  };

  const handlePlayerAction = (action: string) => {
    console.log("Sending action via WebSocket:", action);
    sendAction(action);
  };

  return (
    <div className="flex flex-col md:flex-row flex-1 text-white">
      {/* Connection Status Bar */}
      <div
        className={`fixed top-0 left-0 right-0 z-50 p-2 text-center text-sm font-mono ${
          isConnected ? "bg-green-600 text-white" : "bg-red-600 text-white"
        } transition-all duration-300`}
      >
        {isConnected
          ? "🟢 Connected to Game Server"
          : "🔴 Disconnected - Trying to reconnect..."}
      </div>

      {/* Add top padding to account for status bar */}
      <div className="pt-12 flex flex-col md:flex-row flex-1">
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
          <CharacterPanel playerState={playerState} />
        </div>

        {/* Chat Interface */}
        <div
          className={`flex flex-1 ${
            activeTab !== "chat" ? "hidden md:flex" : ""
          }`}
        >
          <ChatPanel
            onPlayerAction={handlePlayerAction}
            chatHistory={chatHistory}
            isConnected={isConnected}
            slug={slug}
          />
        </div>
      </div>
    </div>
  );
}
