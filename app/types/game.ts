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
  max_hp: number;
  mp: number;
  max_mp: number;
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
  equipped_gear?: EquippedGear;
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
  is_processing?: boolean;
}

export interface GameInfo {
  slug: string;
  title: string;
  description: string;
  player_count: number;
  status: "active" | "maintenance" | "beta";
  difficulty: "beginner" | "intermediate" | "advanced";
  estimated_time: string;
  features: string[];
  thumbnail: string;
  tags: string[];
}

// Will need to add mana later
export interface CharacterState {
  name: string;
  character_type: string;
  max_hp?: number;
  current_hp?: number;
  armor_class?: number;
  level?: number;
  bio: string;
  stats: CharacterAttributes;
}

export interface CharacterAttributes {
  strength: number;
  dexterity: number;
  constitution: number;
  intelligence: number;
  wisdom: number;
  charisma: number;
}

export interface CharacterAbilities {
  id: string;
  name: string;
  icon: string;
  requirement: string;
  req_stat: string;
  req_value: number;
  type: string;
  description: string;
}
