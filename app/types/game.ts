// types/game.ts

export interface CharacterStats {
  strength: number;
  dexterity: number;
  constitution: number;
  intelligence: number;
  wisdom: number;
  charisma: number;
}

export interface Character {
  name: string;
  level: number;
  class: string;
  hp: number;
  maxHp: number;
  mp: number;
  maxMp: number;
  stats: CharacterStats;
}

export interface EquipmentItem {
  name: string;
  defense?: number;
  damage?: string;
  description?: string;
}

export interface EquippedGear {
  helm?: EquipmentItem;
  armor?: EquipmentItem;
  weapon?: EquipmentItem;
  shield?: EquipmentItem;
  hands?: EquipmentItem;
  legs?: EquipmentItem;
}

export interface InventoryItem {
  id: number;
  name: string;
  quantity: number;
  type: "consumable" | "weapon" | "armor" | "misc";
  description?: string;
}

export interface Quest {
  id: number;
  name: string;
  status: "active" | "completed" | "failed";
  progress: string;
  description?: string;
}

export interface CharacterPanelProps {
  character?: Character;
  equippedGear?: EquippedGear;
  inventory?: InventoryItem[];
  quests?: Quest[];
}

export interface GameMessage {
  id: string;
  type: "system" | "player" | "npc" | "scene" | "error";
  content: string;
  timestamp: Date;
  speaker?: string;
}

export interface GameInterfaceProps {
  onPlayerAction?: (action: string) => void;
  isProcessing?: boolean;
}

export interface GameInfo {
  slug: string;
  title: string;
  description: string;
  playerCount: number;
  status: "active" | "maintenance" | "beta";
  difficulty: "beginner" | "intermediate" | "advanced";
  estimatedTime: string;
  features: string[];
  thumbnail: string;
  tags: string[];
}