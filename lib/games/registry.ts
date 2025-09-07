import { ComponentType } from "react";

interface GameComponents {
  MainMenu: () => Promise<{ default: ComponentType<{ slug: string }> }>;
  CreateCharacter: () => Promise<{ default: ComponentType<{ slug: string }> }>;
  GamePage: () => Promise<{
    default: ComponentType<{ slug: string; id: string }>;
  }>;
}

const gameRegistry: Record<string, GameComponents> = {
  mudai: {
    MainMenu: () => import("@/components/games/mudai/MainMenu"),
    CreateCharacter: () => import("@/components/games/mudai/CreateCharacter"),
    GamePage: () => import("@/components/games/mudai/GamePage"),
  },
  // "space-adventure": {
  //   MainMenu: () => import("@/components/games/space-adventure/MainMenu"),
  //   CreateCharacter: () =>
  //     import("@/components/games/space-adventure/CreateCharacter"),
  //   GameInterface: () =>
  //     import("@/components/games/space-adventure/GameInterface"),
  // },
};

export function getGameComponents(slug: string): GameComponents | null {
  return gameRegistry[slug] || null;
}

// Also useful for your lobby
export function getAvailableGames() {
  return Object.keys(gameRegistry);
}
