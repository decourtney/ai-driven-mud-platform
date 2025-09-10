// types/game.ts

export interface EquipmentItem {
  name: string;
  defense?: number;
  damage?: string;
  description?: string;
}

export interface Quest {
  id: number;
  name: string;
  status: "active" | "completed" | "failed";
  progress: string;
  description?: string;
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

export interface ChatMessage {
  id: string;
  speaker: string;
  content: string;
  timestamp: string;
}

export interface GameMessage {
  type: string;
  data: any;
  timestamp: string;
}

export interface GameState {
  // Your game state structure - adjust based on what your backend sends
  player?: {
    name?: string;
    level?: number;
    current_hp?: number;
    max_hp?: number;
    current_mp?: number;
    max_mp?: number;
    strength?: number;
    dexterity?: number;
    constitution?: number;
    intelligence?: number;
    wisdom?: number;
    charisma?: number;
    inventory?: any[];
    [key: string]: any;
  };
  scene?: {
    name?: string;
    description?: string;
    [key: string]: any;
  };
  npcs?: any[];
  [key: string]: any;
}
