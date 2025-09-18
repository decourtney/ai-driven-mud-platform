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

export interface GameState {
  game_id: string;
  player: CharacterState;
  npcs?: CharacterState[];
  scene?: {
    name?: string;
    description?: string;
    [key: string]: any;
  };
  turn_counter: string;
  objectives: string;
  completed_objectives: string;
  story_beats: string;
  in_combat: string;
  initiative_order: string;
  current_turn_character: string;
  weather: string;
  time_of_day: string;
  location_history: string;
  recent_events: string;
  important_npcs_met: string[];
  items_discovered: string;
  session_started: string;
  last_updated: string;
  save_version: string;
}

export interface CharacterState {
  character_id: string;
  name: string;
  character_type: string;
  level: number;
  bio: string;
  max_hp: number;
  current_hp: number;
  temporary_hp: number;
  armor_class: number;
  strength: number;
  dexterity: number;
  constitution: number;
  intelligence: number;
  wisdom: number;
  charisma: number;
  max_mp: number;
  current_mp: number;
  equipped_weapon?: string | null;
  equipped_armor?: string | null;
  inventory: Item[];
  gold: number;
  status_effects: StatusEffects[];
  is_alive: string;
  can_act: string;
  last_updated: string;
}

export interface CharacterConfig {
  name: string;
  strength: number;
  dexterity: number;
  constitution: number;
  intelligence: number;
  wisdom: number;
  charisma: number;
  character_type: string;
  bio: string;
  equipped_weapon?: Item;
  inventory?: Item[]
}

export interface Item {
  id: string;
  name: string;
  item_type?: number;
  description?: string;
  damage_dice?: string;
  armor_class: number;
  gold_value: number;
  weight: number;
}

export interface Quest {
  id: number;
  name: string;
  status: "active" | "completed" | "failed";
  progress: string;
  description?: string;
}

export interface StatusEffects {
  effect: string;
  duration: number;
  intensity: string;
  source: string;
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
