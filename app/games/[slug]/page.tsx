"use client";

import React, { useState, useEffect } from "react";
import {
  Dice1,
  Plus,
  Minus,
  User,
  Scroll,
  Sword,
  Shield,
  Zap,
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
import { CharacterAbilities, CharacterAttributes } from "@/app/types/game";
import Image from "next/image";
import FighterImage from "@/public/images/fighter.webp";

const CharacterCreation = () => {
  const [stats, setStats] = useState<CharacterAttributes>({
    strength: 10,
    dexterity: 10,
    constitution: 10,
    intelligence: 10,
    wisdom: 10,
    charisma: 10,
  });

  const [character, setCharacter] = useState({
    name: "",
    bio: "",
  });

  const [selectedAbilities, setSelectedAbilities] = useState<
    CharacterAbilities[]
  >([]);
  const [availablePoints, setAvailablePoints] = useState(27);

  const getStatCost = (value: number) => {
    if (value <= 13) return value - 8;
    if (value === 14) return 7;
    if (value === 15) return 9;
    return 0;
  };

  const getTotalSpentPoints = () => {
    return Object.values(stats).reduce(
      (total, stat) => total + getStatCost(stat),
      0
    );
  };

  useEffect(() => {
    setAvailablePoints(27 - getTotalSpentPoints());
  }, [stats]);

  const rollStats = () => {
    const rollStat = () => {
      const rolls = Array.from(
        { length: 4 },
        () => Math.floor(Math.random() * 6) + 1
      );
      rolls.sort((a, b) => b - a);
      return rolls.slice(0, 3).reduce((sum, roll) => sum + roll, 0);
    };

    setStats({
      strength: rollStat(),
      dexterity: rollStat(),
      constitution: rollStat(),
      intelligence: rollStat(),
      wisdom: rollStat(),
      charisma: rollStat(),
    });
  };

  const adjustStat = (statName: string, delta: number) => {
    const currentValue = stats[statName as keyof CharacterAttributes];
    const newValue = currentValue + delta;

    if (newValue < 8 || newValue > 15) return;

    const currentCost = getStatCost(currentValue);
    const newCost = getStatCost(newValue);
    const costDiff = newCost - currentCost;

    if (costDiff > availablePoints) return;

    setStats((prev) => ({
      ...prev,
      [statName]: newValue,
    }));
  };

  const getStatModifier = (value: number) => Math.floor((value - 10) / 2);

  const availableAbilities: CharacterAbilities[] = [
    {
      id: "fireball",
      name: "Fireball",
      icon: "🔥",
      requirement: "INT 13+",
      reqStat: "intelligence",
      reqValue: 13,
      type: "spell",
      description: "Launch a burning projectile",
    },
    {
      id: "healing",
      name: "Healing Touch",
      icon: "✨",
      requirement: "WIS 13+",
      reqStat: "wisdom",
      reqValue: 13,
      type: "spell",
      description: "Restore health to yourself or others",
    },
    {
      id: "stealth",
      name: "Stealth",
      icon: "👤",
      requirement: "DEX 12+",
      reqStat: "dexterity",
      reqValue: 12,
      type: "skill",
      description: "Move unseen through shadows",
    },
    {
      id: "intimidate",
      name: "Intimidate",
      icon: "👹",
      requirement: "STR 12+",
      reqStat: "strength",
      reqValue: 12,
      type: "skill",
      description: "Strike fear into enemies",
    },
    {
      id: "lockpick",
      name: "Lockpicking",
      icon: "🗝️",
      requirement: "DEX 14+",
      reqStat: "dexterity",
      reqValue: 14,
      type: "skill",
      description: "Open locked doors and chests",
    },
    {
      id: "detect_magic",
      name: "Detect Magic",
      icon: "🔮",
      requirement: "INT 11+",
      reqStat: "intelligence",
      reqValue: 11,
      type: "spell",
      description: "Sense magical auras and enchantments",
    },
    {
      id: "first_aid",
      name: "First Aid",
      icon: "🩹",
      requirement: "WIS 11+",
      reqStat: "wisdom",
      reqValue: 11,
      type: "skill",
      description: "Treat wounds and ailments",
    },
    {
      id: "weapon_mastery",
      name: "Weapon Mastery",
      icon: "⚔️",
      requirement: "STR 14+",
      reqStat: "strength",
      reqValue: 14,
      type: "combat",
      description: "Enhanced combat techniques",
    },
  ];

  const isAbilityAvailable = (ability: CharacterAbilities) => {
    return (
      stats[ability.reqStat as keyof CharacterAttributes] >= ability.reqValue
    );
  };

  const toggleAbility = (abilityId: CharacterAbilities) => {
    if (selectedAbilities.some((a) => a.id === abilityId.id)) {
      setSelectedAbilities((prev) => prev.filter((a) => a.id !== abilityId.id));
    } else if (selectedAbilities.length < 3) {
      setSelectedAbilities((prev) => [...prev, abilityId]);
    }
  };

  const calculateHP = () => 10 + getStatModifier(stats.constitution);

  const handleCreate = () => {
    const characterData = {
      name: character.name,
      bio: character.bio,
      stats,
      abilities: selectedAbilities,
      hp: calculateHP(),
    };

    console.log("Creating character:", characterData);
    alert("Character created! (This would normally start the game)");
  };

  const getStatIcon = (statName: string) => {
    switch (statName) {
      case "strength":
        return <BicepsFlexed size={14} className="text-red-400" />;
      case "dexterity":
        return <Target size={14} className="text-green-400" />;
      case "constitution":
        return <Heart size={14} className="text-pink-400" />;
      case "intelligence":
        return <Brain size={14} className="text-blue-400" />;
      case "wisdom":
        return <Eye size={14} className="text-purple-400" />;
      case "charisma":
        return <Users size={14} className="text-yellow-400" />;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-black text-white font-mono">
      <div className="mx-auto flex flex-col md:flex-row max-w-7xl">
        {/* Left Panel - Character Panel */}
        <div className="w-full md:w-xl min-h-screen bg-gray-900 border-r border-green-500 flex flex-col">
          <div className="relative h-full z-10 p-4 flex flex-col justify-end border-b border-green-500">
            {/* Character Avatar - Large display area */}
            <div className="absolute inset-0 w-full h-full">
              <img
                src="/images/fighter.webp"
                alt="Picture of a fighter in armor wielding sword and shield"
                className="w-full h-full object-cover"
                style={{
                  filter:
                    "contrast(.8) brightness(0.8) sepia(0.4) saturate(0.7)",
                }}
              />
              {/* Overlay gradient for text readability */}
              <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent"></div>
            </div>

            {/* Name and Bio entries - positioned at bottom */}
            <div className="relative z-10">
              {/* Name Entry */}
              <div className="mb-3">
                <label className="block text-sm text-green-400 mb-1">
                  Name
                </label>
                <input
                  type="text"
                  value={character.name}
                  onChange={(e) =>
                    setCharacter((prev) => ({ ...prev, name: e.target.value }))
                  }
                  className="w-full bg-black/60 backdrop-blur-sm border border-green-500 px-3 py-2 text-green-400 focus:outline-none focus:border-green-300"
                  placeholder="Character name..."
                  maxLength={20}
                />
              </div>

              {/* Bio Entry */}
              <div className="mb-4">
                <label className="block text-sm text-green-400 mb-1">Bio</label>
                <textarea
                  value={character.bio}
                  onChange={(e) =>
                    setCharacter((prev) => ({ ...prev, bio: e.target.value }))
                  }
                  className="w-full bg-black/60 backdrop-blur-sm border border-green-500 px-3 py-2 text-green-400 focus:outline-none focus:border-green-300 resize-none text-sm"
                  placeholder="Character background..."
                  rows={3}
                  maxLength={200}
                />
                <div className="text-xs text-gray-500 text-right">
                  {character.bio.length}/200
                </div>
              </div>
            </div>
          </div>

          {/* Character Stats Summary */}
          <div className="p-4 bg-gray-800 hidden md:block">
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
                  className={`${
                    availablePoints >= 0 ? "text-green-400" : "text-red-400"
                  }`}
                >
                  {availablePoints}
                </span>
              </div>
            </div>

            <button
              onClick={handleCreate}
              disabled={!character.name.trim() || availablePoints < 0}
              className="w-full mt-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-black font-bold py-3 transition-colors"
            >
              CREATE CHARACTER
            </button>
          </div>
        </div>

        {/* Right Panel - Stats & Abilities */}
        <div className="flex-1 min-h-screen flex flex-col">
          {/* Gear Section */}
          <div className="bg-gray-900 border-b border-green-500 p-4 flex-1">
            <h3 className="text-green-400 font-mono font-bold mb-4">
              STARTING GEAR
            </h3>

            {/* Equipment Grid */}
            <div className="grid grid-cols-5 gap-2 mb-4 md:px-10 auto-rows-[3rem]">
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

            {/* Starting inventory items */}
            <div className="w-80 grid grid-cols-4 gap-2 mb-4 mx-auto auto-rows-[4rem]">
              <div className="bg-gray-800 border border-gray-600 "></div>
              <div className="bg-gray-800 border border-gray-600 "></div>
              <div className="bg-gray-800 border border-gray-600 "></div>
              <div className="bg-gray-800 border border-gray-600 "></div>
            </div>
          </div>

          {/* Attributes Section - Compact */}
          <div className="bg-gray-900 border-b border-green-500 p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-md font-bold text-green-400">ATTRIBUTES</h3>
              <div className="text-xs text-gray-400">
                Points: {availablePoints}
              </div>
              <button
                onClick={rollStats}
                className="bg-green-600 hover:bg-green-700 text-black font-bold px-2 py-1 text-sm transition-colors flex items-center gap-1"
              >
                <Dice1 size={14} />
                ROLL
              </button>
            </div>

            <div className="grid grid-cols-6 gap-2">
              {Object.entries(stats).map(([statName, value]) => {
                const modifier = getStatModifier(value);
                const modifierText =
                  modifier >= 0 ? `+${modifier}` : `${modifier}`;
                const canIncrease =
                  value < 15 &&
                  getStatCost(value + 1) - getStatCost(value) <=
                    availablePoints;
                const canDecrease = value > 8;

                return (
                  <div
                    key={statName}
                    className="bg-gray-800 border border-gray-600 rounded p-2 relative"
                  >
                    {/* Increase button - top half */}
                    <div
                      onClick={() => canIncrease && adjustStat(statName, 1)}
                      className={`absolute inset-x-0 top-0 h-1/2 cursor-pointer transition-colors ${
                        canIncrease ? "hover:bg-gray-700" : "cursor-not-allowed"
                      } flex items-center justify-center`}
                    >
                      {canIncrease && (
                        <ChevronUp
                          size={12}
                          className="text-gray-400 opacity-0 hover:opacity-100 transition-opacity"
                        />
                      )}
                    </div>

                    {/* Decrease button - bottom half */}
                    <div
                      onClick={() => canDecrease && adjustStat(statName, -1)}
                      className={`absolute inset-x-0 bottom-0 h-1/2 cursor-pointer transition-colors ${
                        canDecrease ? "hover:bg-gray-700" : "cursor-not-allowed"
                      } flex items-center justify-center`}
                    >
                      {canDecrease && (
                        <ChevronDown
                          size={12}
                          className="text-gray-400 opacity-0 hover:opacity-100 transition-opacity"
                        />
                      )}
                    </div>

                    {/* Content */}
                    <div className="text-center relative z-10 pointer-events-none">
                      <div className="flex items-center justify-center gap-1 mb-1">
                        {getStatIcon(statName)}
                        <div className="text-xs text-gray-400 uppercase">
                          {statName.slice(0, 3)}
                        </div>
                      </div>
                      <div className="text-lg font-bold text-white">
                        {value}
                      </div>
                      <div className="text-xs text-gray-400">
                        ({modifierText})
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Abilities Section - Compact */}
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
                  <div
                    key={ability.id}
                    onClick={() => available && toggleAbility(ability)}
                    className={`relative p-2 rounded border cursor-pointer transition-all text-center ${
                      available
                        ? selected
                          ? "border-green-500 bg-green-900/30"
                          : "border-gray-600 hover:border-green-400 bg-gray-800"
                        : "border-gray-700 bg-gray-800/50 cursor-not-allowed opacity-50"
                    }`}
                    title={`${ability.name} - ${ability.requirement}`}
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
                  </div>
                );
              })}
            </div>
          </div>

          {/* Character Stats Summary */}
          <div className="p-4 bg-gray-800 md:hidden">
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
                  className={`${
                    availablePoints >= 0 ? "text-green-400" : "text-red-400"
                  }`}
                >
                  {availablePoints}
                </span>
              </div>
            </div>

            <button
              onClick={handleCreate}
              disabled={!character.name.trim() || availablePoints < 0}
              className="w-full mt-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-black font-bold py-3 transition-colors"
            >
              CREATE CHARACTER
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CharacterCreation;
