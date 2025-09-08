// Enhanced GamePage.tsx with pipeline processing
"use client";

import CharacterPanel from "@/components/games/mudai/CharacterPanel";
import ChatInterface from "@/components/games/mudai/ChatInterface";
import {
  Character,
  EquippedGear,
  InventoryItem,
  Quest,
  GameMessage,
} from "@/app/types/game";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

interface GamePageProps {
  slug: string;
  id: string;
}

interface ActionResponse {
  userNarration: string;
  aiWillAct: boolean;
  aiActionId?: string; // For tracking the AI's pending action
  gameState?: any; // Updated game state if needed
}

interface AiActionResponse {
  aiNarration: string;
  gameState?: any;
}

export default function GamePage({ slug, id }: GamePageProps) {
  const [gameState, setGameState] = useState();
  const [activeTab, setActiveTab] = useState<"character" | "feed">("character");
  const [gameMessages, setGameMessages] = useState<GameMessage[]>([
    {
      id: "1",
      type: "scene",
      content:
        "You find yourself standing at the entrance of a dark, foreboding dungeon. Ancient stone walls drip with moisture, and the air carries the musty scent of ages past. Flickering torchlight dances across carved symbols that seem to watch your every move.",
      timestamp: new Date(),
    },
    {
      id: "2",
      type: "system",
      content:
        "Welcome to MudAI! Type your actions to interact with the world.",
      timestamp: new Date(),
    },
  ]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [pendingAiAction, setPendingAiAction] = useState<string | null>(null);

  const addMessage = (message: Omit<GameMessage, "id" | "timestamp">) => {
    const newMessage: GameMessage = {
      ...message,
      id: Date.now().toString() + Math.random(),
      timestamp: new Date(),
    };
    setGameMessages((prev) => [...prev, newMessage]);
  };

  const handlePlayerAction = async (action: string) => {
    console.log("Player action:", action);

    // Add player message immediately
    addMessage({
      type: "player",
      content: action,
      speaker: "You",
    });

    setIsProcessing(true);

    try {
      // Step 1: Send user action for parsing and narration
      const res = await fetch(`/api/play/${slug}/${id}/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(errorText);
      }

      const data: ActionResponse = await res.json();

      // Step 2: Display user action narration immediately
      addMessage({
        type: "scene",
        content: data.userNarration,
      });

      // Step 3: Update game state if provided
      if (data.gameState) {
        setGameState(data.gameState);
      }

      // Step 4: Check if AI will act
      if (data.aiWillAct && data.aiActionId) {
        // Keep input disabled, but user can read the narration
        setPendingAiAction(data.aiActionId);

        // Add a subtle indicator that AI is thinking
        addMessage({
          type: "system",
          content: "The world stirs with activity...",
        });

        // Process AI action in the background
        handleAiAction(data.aiActionId);
      } else {
        // No AI action needed, unlock input
        setIsProcessing(false);
      }
    } catch (err: any) {
      toast.error(err.message || "Something went wrong");
      addMessage({
        type: "error",
        content: `Error: ${err.message || "Something went wrong"}`,
      });
      setIsProcessing(false);
    }
  };

  const handleAiAction = async (actionId: string) => {
    try {
      // This runs in the background while user reads their action narration
      const res = await fetch(
        `/api/play/${slug}/${id}/ai-action/${actionId}`,
        {
          method: "GET",
        }
      );

      if (!res.ok) {
        throw new Error("AI action failed");
      }

      const data: AiActionResponse = await res.json();

      // Display AI narration
      addMessage({
        type: "scene", // or "npc" depending on what happened
        content: data.aiNarration,
      });

      // Update game state if provided
      if (data.gameState) {
        setGameState(data.gameState);
      }
    } catch (err: any) {
      console.error("AI action error:", err);
      addMessage({
        type: "error",
        content: "Something unexpected happened...",
      });
    } finally {
      // Always unlock input after AI action completes
      setPendingAiAction(null);
      setIsProcessing(false);
    }
  };

  // Rest of your component remains the same
  const character: Character = {
    name: "Aragorn",
    level: 12,
    class: "Ranger",
    hp: 85,
    max_hp: 100,
    mp: 40,
    max_mp: 60,
    stats: {
      strength: 16,
      dexterity: 14,
      constitution: 15,
      intelligence: 12,
      wisdom: 13,
      charisma: 11,
    },
  };

  const equippedGear: EquippedGear = {
    helm: { name: "Iron Helm", defense: 3 },
    armor: { name: "Chainmail Armor", defense: 8 },
    hands: { name: "Leather Gloves", defense: 1 },
    legs: { name: "Steel Greaves", defense: 4 },
    weapon: { name: "Elven Sword", damage: "1d8+2" },
    shield: { name: "Round Shield", defense: 2 },
  };

  const inventory: InventoryItem[] = [
    { id: 1, name: "Health Potion", quantity: 3, type: "consumable" },
  ];

  const quests: Quest[] = [
    { id: 1, name: "Rescue the Princess", status: "active", progress: "2/3" },
  ];

  return (
    <div className="flex flex-col md:flex-row flex-1 text-white">
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
      <div
        className={`flex flex-1 ${
          activeTab !== "feed" ? "hidden md:flex" : ""
        }`}
      >
        <ChatInterface
          onPlayerAction={handlePlayerAction}
          is_processing={isProcessing}
          gameMessages={gameMessages}
          pendingAiAction={pendingAiAction}
        />
      </div>
    </div>
  );
}
