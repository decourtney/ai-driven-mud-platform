"use client";

import CharacterPanel from "@/components/games/mudai/CharacterPanel";
import ChatInterface from "@/components/games/mudai/ChatInterface";
import {
  Character,
  EquippedGear,
  InventoryItem,
  Quest,
} from "@/app/types/game";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

interface GamePageProps {
  slug: string;
  id: string;
}

export default function GamePage({ slug, id }: GamePageProps) {
  const [engineId, setEngineId] = useState<string | null>(null);
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [playerState, setPlayerState] = useState<PlayerState | null>(null);
  const [npcsState, setNpcsState] = useState<CharacterState[] | null>([]);
  const [sceneState, setSceneState] = useState<SceneState | null>(null);
  const [activeTab, setActiveTab] = useState<"character" | "chat">("character");
  const [isProcessing, setIsProcessing] = useState(false);

  // Load game state from localStorage on component mount
  useEffect(() => {
    const gameData = `${slug}Session`;

    try {
      const savedData = localStorage.getItem(gameData);
      if (savedData) {
        const parsedData = JSON.parse(savedData);
        setEngineId(parsedData.engine_id);
        setGameState(parsedData.game_state);
        setPlayerState(parsedData.game_state.player);
        setNpcsState(parsedData.game_state.npcs);
        setSceneState(parsedData.game_state.scene);
        console.log("Loaded game state from localStorage:", parsedData);
      } else {
        console.log("No saved game state found");
        // You might want to redirect to character creation or load default state
      }
    } catch (error) {
      console.error("Error loading game state from localStorage:", error);
      toast.error("Failed to load game state");
    }
  }, [slug, id]);

  const handlePlayerAction = async (action: string) => {
    console.log("Player action:", action);
    try {
      const res = await fetch(`/api/play/${slug}/${id}/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(action),
      });

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(errorText);
      }

      const data = await res.json();
      console.log(data)

    } catch (err: any) {
      toast.error(err.message || "Something went wrong");
    } finally {
      setIsProcessing(false);
    }
  };

  // Save game state to localStorage whenever it changes
  const saveGameState = (newState: GameState) => {
    const gameData = `${slug}Session`;
    try {
      localStorage.setItem(gameData, JSON.stringify(newState));
      setGameState(newState);
      console.log("Game state saved to localStorage");
    } catch (error) {
      console.error("Error saving game state to localStorage:", error);
      toast.error("Failed to save game state");
    }
  };

  // Don't render until game state is loaded
  if (!gameState) {
    return (
      <div className="flex items-center justify-center flex-1 text-white">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-500 mb-4"></div>
          <p className="text-green-400 font-mono">Loading game state...</p>
        </div>
      </div>
    );
  }

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
            activeTab === "feed" ? "bg-gray-800" : "bg-gray-900"
          }`}
          onClick={() => setActiveTab("feed")}
        >
          Feed
        </button>
      </div>

      {/* Character Panel */}
      <div
        className={`flex flex-1 md:flex-initial md:w-150 ${
          activeTab !== "character" ? "hidden md:flex" : ""
        }`}
      >
        <CharacterPanel
          character={character}
          equipped_gear={equippedGear}
          inventory={inventory}
          quests={quests}
        />
      </div>

      {/* Chat Interface */}
      <div className={`flex flex-1 min-h-0 ${ activeTab !== "chat" ? "hidden md:flex" : "" }`}>
        <ChatInterface
          onPlayerAction={handlePlayerAction}
          isProcessing={isProcessing}
          scene={sceneState!}
          npcs={npcsState!}
        />
      </div>
    </div>
  );
}
