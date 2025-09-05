"use client";

import CharacterPanel from "@/app/components/game/CharacterPanel";
import GameInterface from "@/app/components/game/GameInterface";
import {
  Character,
  EquippedGear,
  InventoryItem,
  Quest,
} from "../../../types/game";

export default function GamePage() {
  const handlePlayerAction = (action: string) => {
    console.log("Player action:", action);
    // This will connect to your FastAPI backend later
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
    <div className="min-h-screen bg-black text-white flex">
      <CharacterPanel
        character={character}
        equipped_gear={equippedGear}
        inventory={inventory}
        quests={quests}
      />

      <GameInterface
        onPlayerAction={handlePlayerAction}
        is_processing={false} // Set to true when waiting for backend response
      />
    </div>
  );
}
