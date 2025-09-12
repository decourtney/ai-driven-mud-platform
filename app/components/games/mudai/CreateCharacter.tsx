"use client";

import React, { useState, useEffect } from "react";
import {
  Plus,
  Minus,
  User,
  Sword,
  Shield,
  Eye,
  Heart,
  Brain,
  BicepsFlexed,
  Target,
  Users,
  Crown,
  ChevronUp,
  ChevronDown,
} from "lucide-react";
import { CharacterAbilities } from "@/app/types/game";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { NewCharacter } from "@/app/types/game";

interface CreateCharacterProps {
  slug: string;
}

type StatName =
  | "strength"
  | "dexterity"
  | "constitution"
  | "intelligence"
  | "wisdom"
  | "charisma";

export default function CreateCharacter({ slug }: CreateCharacterProps) {
  const router = useRouter();

  const [playerState, setPlayerState] = useState<NewCharacter>({
    name: "User",
    strength: 15,
    dexterity: 13,
    constitution: 14,
    intelligence: 10,
    wisdom: 10,
    charisma: 10,
    character_type: "player",
    bio: "",
    inventory: [],
  });

  const [selectedAbilities, setSelectedAbilities] = useState<
    CharacterAbilities[]
  >([]);
  const [availablePoints, setAvailablePoints] = useState(27);

  // Recalculate available points when stats change
  useEffect(() => {
    const totalSpent = getTotalSpentPoints();
    setAvailablePoints(27 - totalSpent);
  }, [
    playerState.strength,
    playerState.dexterity,
    playerState.constitution,
    playerState.intelligence,
    playerState.wisdom,
    playerState.charisma,
  ]);

  const handleSubmit = async () => {
    try {
      const res = await fetch(`/api/play/${slug}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(playerState),
      });

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(errorText);
      }

      const data = await res.json();
      router.push(`/play/${slug}/${data.session_id}`);
    } catch (err: any) {
      toast.error(err.message || "Something went wrong");
    }
  };

  const adjustStat = (statName: StatName, delta: number) => {
    const currentValue = playerState[statName];
    const newValue = currentValue + delta;

    // Check bounds
    if (newValue < 8 || newValue > 15) return;

    // Check if we have enough points
    const currentCost = getStatCost(currentValue);
    const newCost = getStatCost(newValue);
    const costDiff = newCost - currentCost;

    if (costDiff > availablePoints) return;

    setPlayerState((prev) => ({
      ...prev,
      [statName]: newValue,
    }));
  };

  const getStatCost = (value: number) => {
    if (value <= 13) return value - 8;
    if (value === 14) return 7;
    if (value === 15) return 9;
    return 0;
  };

  const getTotalSpentPoints = () => {
    const stats = [
      playerState.strength,
      playerState.dexterity,
      playerState.constitution,
      playerState.intelligence,
      playerState.wisdom,
      playerState.charisma,
    ];
    return stats.reduce((total, stat) => total + getStatCost(stat), 0);
  };

  const calculateHP = () => 10 + getStatModifier(playerState.constitution);

  const getStatModifier = (value: number) => Math.floor((value - 10) / 2);

  const isAbilityAvailable = (ability: CharacterAbilities) => {
    return playerState[ability.req_stat as StatName] >= ability.req_value;
  };

  const toggleAbility = (ability: CharacterAbilities) => {
    if (selectedAbilities.some((a) => a.id === ability.id)) {
      setSelectedAbilities((prev) => prev.filter((a) => a.id !== ability.id));
    } else if (selectedAbilities.length < 3) {
      setSelectedAbilities((prev) => [...prev, ability]);
    }
  };

  const getStatIcon = (statName: StatName) => {
    const iconMap = {
      strength: <BicepsFlexed size={14} className="text-red-400" />,
      dexterity: <Target size={14} className="text-green-400" />,
      constitution: <Heart size={14} className="text-pink-400" />,
      intelligence: <Brain size={14} className="text-blue-400" />,
      wisdom: <Eye size={14} className="text-purple-400" />,
      charisma: <Users size={14} className="text-yellow-400" />,
    };
    return iconMap[statName];
  };

  const availableAbilities: CharacterAbilities[] = [
    {
      id: "fireball",
      name: "Fireball",
      icon: "🔥",
      requirement: "INT 13+",
      req_stat: "intelligence",
      req_value: 13,
      type: "spell",
      description: "Launch a burning projectile",
    },
    {
      id: "healing",
      name: "Healing Touch",
      icon: "✨",
      requirement: "WIS 13+",
      req_stat: "wisdom",
      req_value: 13,
      type: "spell",
      description: "Restore health to yourself or others",
    },
    {
      id: "stealth",
      name: "Stealth",
      icon: "👤",
      requirement: "DEX 12+",
      req_stat: "dexterity",
      req_value: 12,
      type: "skill",
      description: "Move unseen through shadows",
    },
    {
      id: "intimidate",
      name: "Intimidate",
      icon: "👹",
      requirement: "STR 12+",
      req_stat: "strength",
      req_value: 12,
      type: "skill",
      description: "Strike fear into enemies",
    },
    {
      id: "lockpick",
      name: "Lockpicking",
      icon: "🗝️",
      requirement: "DEX 14+",
      req_stat: "dexterity",
      req_value: 14,
      type: "skill",
      description: "Open locked doors and chests",
    },
    {
      id: "detect_magic",
      name: "Detect Magic",
      icon: "🔮",
      requirement: "INT 11+",
      req_stat: "intelligence",
      req_value: 11,
      type: "spell",
      description: "Sense magical auras and enchantments",
    },
    {
      id: "first_aid",
      name: "First Aid",
      icon: "🩹",
      requirement: "WIS 11+",
      req_stat: "wisdom",
      req_value: 11,
      type: "skill",
      description: "Treat wounds and ailments",
    },
    {
      id: "weapon_mastery",
      name: "Weapon Mastery",
      icon: "⚔️",
      requirement: "STR 14+",
      req_stat: "strength",
      req_value: 14,
      type: "combat",
      description: "Enhanced combat techniques",
    },
  ];

  const statEntries: [StatName, number][] = [
    ["strength", playerState.strength],
    ["dexterity", playerState.dexterity],
    ["constitution", playerState.constitution],
    ["intelligence", playerState.intelligence],
    ["wisdom", playerState.wisdom],
    ["charisma", playerState.charisma],
  ];

  return (
    <div className="flex flex-col md:flex-row flex-1 max-w-7xl mx-auto text-white font-mono">
      <div className="absolute backdrop-blur-xs inset-0 w-full h-full bg-black/30 -z-10"></div>

      {/* Left Panel - Character Image & Details */}
      <div className="flex flex-col w-full md:w-xl bg-gray-900 md:border-r md:border-l border-green-500">
        <div className="relative flex-1 w-full min-h-dvh md:min-h-auto">
          <img
            src="/images/fighter.jpeg"
            alt="Fighter in armor with sword and shield"
            className="absolute w-full h-full object-cover"
            style={{
              filter: "contrast(1.1) brightness(0.4) sepia(0.7) saturate(0.8)",
            }}
          />

          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent"></div>

          {/* Character Details Form */}
          <div className="absolute bottom-0 w-full p-4 z-0">
            <div className="mb-3">
              <label className="block text-sm text-green-400 mb-1">Name</label>
              <input
                type="text"
                value={playerState.name}
                onChange={(e) =>
                  setPlayerState((prev) => ({ ...prev, name: e.target.value }))
                }
                className="w-full bg-black/60 backdrop-blur-sm border border-green-500 px-3 py-2 text-green-400 focus:outline-none focus:border-green-300"
                placeholder="Character name..."
                maxLength={20}
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm text-green-400 mb-1">Bio</label>
              <textarea
                value={playerState.bio}
                onChange={(e) =>
                  setPlayerState((prev) => ({ ...prev, bio: e.target.value }))
                }
                className="w-full bg-black/60 backdrop-blur-sm border border-green-500 px-3 py-2 text-green-400 focus:outline-none focus:border-green-300 resize-none text-sm"
                placeholder="Character background..."
                rows={3}
                maxLength={200}
              />
              <div className="text-xs text-gray-500 text-right">
                {playerState.bio.length}/200
              </div>
            </div>
          </div>
        </div>

        {/* Character Stats Summary - Desktop */}
        <div className="p-4 bg-gray-800 hidden md:block border-t border-green-500">
          <div className="text-sm space-y-1">
            <div className="flex justify-between">
              <span className="text-gray-400">Hit Points:</span>
              <span className="text-red-400">{calculateHP()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Abilities:</span>
              <span className="text-yellow-400">
                {selectedAbilities.length}/3
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Points Left:</span>
              <span
                className={
                  availablePoints >= 0 ? "text-green-400" : "text-red-400"
                }
              >
                {availablePoints}
              </span>
            </div>
          </div>

          <button
            onClick={handleSubmit}
            disabled={!playerState.name.trim() || availablePoints !== 0}
            className="w-full mt-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-black font-bold py-3 transition-colors"
          >
            CREATE CHARACTER
          </button>
        </div>
      </div>

      {/* Right Panel - Stats & Abilities */}
      <div className="flex flex-col md:border-r border-green-500">
        {/* Starting Gear Section */}
        <div className="flex-1 bg-gray-900 border-b border-green-500 p-4">
          <h3 className="text-green-400 font-mono font-bold mb-4">
            STARTING GEAR
          </h3>

          {/* Equipment Preview Grid */}
          <div className="grid grid-cols-5 gap-2 mb-4 md:px-10 auto-rows-fr">
            {/* Helm */}
            <div className="bg-gray-800 border border-gray-600 rounded p-2 flex flex-col items-center justify-center row-start-1 row-span-2 col-start-3">
              <Crown size={16} className="text-gray-400 mb-1" />
              <div className="text-xs text-gray-500">helm</div>
            </div>

            {/* Weapon */}
            <div className="bg-gray-800 border border-gray-600 rounded p-2 flex flex-col items-center justify-center row-start-3 row-span-4 col-start-2">
              <Sword size={16} className="text-gray-400 mb-1" />
              <div className="text-xs text-gray-500">weapon</div>
            </div>

            {/* Armor */}
            <div className="bg-gray-800 border border-gray-600 rounded p-2 flex flex-col items-center justify-center row-start-3 row-span-3 col-start-3">
              <Shield size={16} className="text-gray-400 mb-1" />
              <div className="text-xs text-gray-500">armor</div>
            </div>

            {/* Shield */}
            <div className="bg-gray-800 border border-gray-600 rounded p-2 flex flex-col items-center justify-center row-start-3 row-span-4 col-start-4">
              <Shield size={16} className="text-gray-400 mb-1" />
              <div className="text-xs text-gray-500">shield</div>
            </div>

            {/* Hands */}
            <div className="bg-gray-800 border border-gray-600 rounded p-2 flex flex-col items-center justify-center row-start-7 row-span-2 col-start-2">
              <User size={16} className="text-gray-400 mb-1" />
              <div className="text-xs text-gray-500">hands</div>
            </div>

            {/* Legs */}
            <div className="bg-gray-800 border border-gray-600 rounded p-2 flex flex-col items-center justify-center row-start-6 row-span-3 col-start-3">
              <Shield size={16} className="text-gray-400 mb-1" />
              <div className="text-xs text-gray-500">legs</div>
            </div>

            {/* Feet */}
            <div className="bg-gray-800 border border-gray-600 rounded p-2 flex flex-col items-center justify-center row-start-7 row-span-2 col-start-4">
              <User size={16} className="text-gray-400 mb-1" />
              <div className="text-xs text-gray-500">feet</div>
            </div>
          </div>

          {/* Starting inventory preview */}
          <div className="w-80 grid grid-cols-4 gap-2 mb-4 mx-auto auto-rows-[4rem]">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="bg-gray-800 border border-gray-600"></div>
            ))}
          </div>
        </div>

        {/* Attributes Section */}
        <div className="bg-gray-900 border-b border-green-500 p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-md font-bold text-green-400">ATTRIBUTES</h3>
            <div className="text-xs text-gray-400">
              Points Remaining: {availablePoints}
            </div>
          </div>

          <div className="grid grid-cols-6 gap-2">
            {statEntries.map(([statName, value]) => {
              const modifier = getStatModifier(value);
              const modifierText =
                modifier >= 0 ? `+${modifier}` : `${modifier}`;
              const canIncrease =
                value < 15 &&
                getStatCost(value + 1) - getStatCost(value) <= availablePoints;
              const canDecrease = value > 8;

              return (
                <div
                  key={statName}
                  className="bg-gray-800 border border-gray-600 rounded p-2 relative"
                >
                  {/* Increase button */}
                  <button
                    onClick={() => canIncrease && adjustStat(statName, 1)}
                    disabled={!canIncrease}
                    className={`absolute inset-x-0 top-0 h-1/2 transition-colors ${
                      canIncrease
                        ? "hover:bg-gray-700 cursor-pointer"
                        : "cursor-not-allowed"
                    } flex items-center justify-center`}
                  >
                    {canIncrease && (
                      <ChevronUp size={12} className="text-gray-400" />
                    )}
                  </button>

                  {/* Decrease button */}
                  <button
                    onClick={() => canDecrease && adjustStat(statName, -1)}
                    disabled={!canDecrease}
                    className={`absolute inset-x-0 bottom-0 h-1/2 transition-colors ${
                      canDecrease
                        ? "hover:bg-gray-700 cursor-pointer"
                        : "cursor-not-allowed"
                    } flex items-center justify-center`}
                  >
                    {canDecrease && (
                      <ChevronDown size={12} className="text-gray-400" />
                    )}
                  </button>

                  {/* Stat display */}
                  <div className="text-center relative z-10 pointer-events-none">
                    <div className="flex items-center justify-center gap-1 mb-1">
                      {getStatIcon(statName)}
                      <div className="text-xs text-gray-400 uppercase">
                        {statName.slice(0, 3)}
                      </div>
                    </div>
                    <div className="text-lg font-bold text-white">{value}</div>
                    <div className="text-xs text-gray-400">
                      ({modifierText})
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Abilities Section */}
        <div className="bg-gray-900 p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-md font-bold text-green-400">
              STARTING ABILITIES
            </h3>
            <div className="text-xs text-gray-400">
              Select up to 3 ({selectedAbilities.length}/3)
            </div>
          </div>

          <div className="grid grid-cols-4 gap-2">
            {availableAbilities.map((ability) => {
              const available = isAbilityAvailable(ability);
              const selected = selectedAbilities.some(
                (a) => a.id === ability.id
              );

              return (
                <button
                  key={ability.id}
                  onClick={() => available && toggleAbility(ability)}
                  disabled={!available}
                  className={`relative p-2 rounded border transition-all text-center ${
                    available
                      ? selected
                        ? "border-green-500 bg-green-900/30"
                        : "border-gray-600 hover:border-green-400 bg-gray-800"
                      : "border-gray-700 bg-gray-800/50 cursor-not-allowed opacity-50"
                  }`}
                  title={`${ability.name} - ${ability.requirement}\n${ability.description}`}
                >
                  {selected && (
                    <div className="absolute -top-1 -right-1 bg-green-500 text-white text-xs w-4 h-4 rounded-full flex items-center justify-center">
                      ✓
                    </div>
                  )}

                  <div className="text-lg mb-1">{ability.icon}</div>
                  <div
                    className={`text-xs ${
                      available ? "text-white" : "text-gray-500"
                    }`}
                  >
                    {ability.name}
                  </div>
                  <div className="text-xs text-gray-500">
                    {ability.requirement}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Character Stats Summary - Mobile */}
        <div className="p-4 bg-gray-800 md:hidden border-t border-green-500">
          <div className="text-sm space-y-1">
            <div className="flex justify-between">
              <span className="text-gray-400">Hit Points:</span>
              <span className="text-red-400">{calculateHP()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Abilities:</span>
              <span className="text-yellow-400">
                {selectedAbilities.length}/3
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Points Left:</span>
              <span
                className={
                  availablePoints >= 0 ? "text-green-400" : "text-red-400"
                }
              >
                {availablePoints}
              </span>
            </div>
          </div>

          <button
            onClick={handleSubmit}
            disabled={!playerState.name.trim() || availablePoints !== 0}
            className="w-full mt-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-black font-bold py-3 transition-colors"
          >
            CREATE CHARACTER
          </button>
        </div>
      </div>
    </div>
  );
}
