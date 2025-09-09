"use client";

import CharacterPanel from "@/components/games/mudai/CharacterPanel";
import ChatInterface from "@/components/games/mudai/ChatInterface";
import {
  Character,
  CharacterState,
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
  const [gameState, setGameState] = useState<CharacterState | null>(null);
  const [activeTab, setActiveTab] = useState<"character" | "feed">("character");
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    const gameStateKey = `${slug}Session`;

    try {
      const savedState = localStorage.getItem(gameStateKey);
      if (savedState) {
        console.log("Saved game state: ", savedState);
        const parsedState = JSON.parse(savedState);
        setGameState(parsedState);
        console.log("Loaded game state from localStorage:", parsedState);
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
      console.log(data);
    } catch (err: any) {
      toast.error(err.message || "Something went wrong");
    }
  };

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
    // ... rest of inventory
  ];

  const quests: Quest[] = [
    { id: 1, name: "Rescue the Princess", status: "active", progress: "2/3" },
    // ... rest of quests
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

      {/* feed Interface */}
      <div
        className={`flex flex-1 ${
          activeTab !== "feed" ? "hidden md:flex" : ""
        }`}
      >
        <ChatInterface
          onPlayerAction={handlePlayerAction}
          is_processing={false}
        />
      </div>
    </div>
  );
}
