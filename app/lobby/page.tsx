"use server";

import React from "react";
import Link from "next/link";
import { Play, Users, Clock, Star } from "lucide-react";
import { GameInfo } from "@/app/types/game";
import axios from "axios";
import { notFound } from "next/navigation";

export default async function LobbyPage() {
  const res = await axios
    .get(`${process.env.NEXT_PUBLIC_BASE_URL}/games`)
    .catch(() => notFound());
  const games: GameInfo[] = res.data;
  const featuredGame =
    games.find((game) => game.tags?.includes("featured")) ?? games[0];
  const upcomingGames = games.filter((game) => game.tags?.includes("upcoming"));

  const getStatusBadge = (status: GameInfo["status"]) => {
    switch (status) {
      case "active":
        return "bg-green-600 text-white";
      case "beta":
        return "bg-yellow-600 text-white";
      case "maintenance":
        return "bg-red-600 text-white";
      default:
        return "bg-gray-600 text-white";
    }
  };

  const getDifficultyColor = (difficulty: GameInfo["difficulty"]) => {
    switch (difficulty) {
      case "beginner":
        return "text-green-400";
      case "intermediate":
        return "text-yellow-400";
      case "advanced":
        return "text-red-400";
      default:
        return "text-gray-400";
    }
  };

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="max-w-6xl mx-auto p-6">
        {/* Featured Game Section */}
        <section className="mb-12">
          <div className="bg-gray-900 border-2 border-green-500 rounded-lg overflow-hidden hover:border-green-400 transition-colors">
            <div className="p-8">
              <div className="flex flex-col lg:flex-row gap-8">
                {/* Game Info */}
                <div className="flex-1">
                  <div className="flex items-center gap-4 mb-4">
                    <h3 className="text-3xl font-mono font-bold text-white">
                      {featuredGame.title}
                    </h3>
                    <span
                      className={`px-3 py-1 rounded font-mono text-sm font-bold ${getStatusBadge(
                        featuredGame.status
                      )}`}
                    >
                      {featuredGame.status.toUpperCase()}
                    </span>
                  </div>

                  <p className="text-gray-300 font-mono mb-6 leading-relaxed text-lg">
                    {featuredGame.description}
                  </p>

                  {/* Game Stats */}
                  <div className="flex flex-wrap gap-6 mb-6 text-sm font-mono">
                    <div className="flex items-center text-green-400">
                      <Users size={16} className="mr-2" />
                      {featuredGame.playerCount} players online
                    </div>
                    <div className="flex items-center text-cyan-400">
                      <Clock size={16} className="mr-2" />
                      {featuredGame.estimatedTime}
                    </div>
                    <div
                      className={`flex items-center ${getDifficultyColor(
                        featuredGame.difficulty
                      )}`}
                    >
                      <Star size={16} className="mr-2" />
                      {featuredGame.difficulty}
                    </div>
                  </div>

                  {/* Features */}
                  <div className="mb-6">
                    <h4 className="text-green-400 font-mono font-bold mb-3">
                      Game Features:
                    </h4>
                    <div className="grid grid-cols-2 gap-2">
                      {featuredGame.features.map((feature, index) => (
                        <div
                          key={index}
                          className="text-gray-300 font-mono text-sm flex items-center"
                        >
                          <span className="text-green-400 mr-2">→</span>
                          {feature}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Play Button */}
                  <Link href={`games/${featuredGame.slug}`}>
                    <button className="bg-green-600 hover:bg-green-700 text-black font-mono font-bold px-8 py-4 text-lg transition-colors flex items-center border-2 border-green-400">
                      <Play size={24} className="mr-3" />[ START ADVENTURE ]
                    </button>
                  </Link>
                </div>

                {/* Game Preview/Thumbnail */}
                <div className="lg:w-96">
                  <div className="bg-gray-800 border-2 border-gray-600 rounded-lg p-6 h-full flex flex-col justify-center items-center">
                    <div className="text-center">
                      <div className="text-8xl mb-4">🏰</div>
                      <div className="text-green-400 font-mono font-bold mb-2">
                        Live Preview
                      </div>
                      <div className="text-gray-400 font-mono text-sm">
                        Experience rich storytelling and dynamic gameplay
                      </div>
                      {/* Terminal-style preview */}
                      <div className="bg-black border border-green-500 rounded p-4 mt-4 text-left">
                        <div className="text-green-400 font-mono text-xs">
                          <div className="mb-1">&gt; look around</div>
                          <div className="text-gray-300 mb-2">
                            You stand in a moonlit forest clearing...
                          </div>
                          <div className="mb-1">&gt; examine tree</div>
                          <div className="text-gray-300">
                            Ancient runes glow softly on the bark...
                          </div>
                          <div className="animate-pulse">_</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Coming Soon Section */}
        <section>
          <h2 className="text-2xl font-mono font-bold text-gray-400 mb-6">
            Coming Soon
          </h2>
          <div className="grid md:grid-cols-2 gap-6">
            {upcomingGames.map((game) => (
              <div
                key={game.slug}
                className="bg-gray-900 border border-gray-600 rounded-lg p-6 opacity-75"
              >
                <div className="flex items-center gap-3 mb-3">
                  <h3 className="text-xl font-mono font-bold text-white">
                    {game.title}
                  </h3>
                  <span
                    className={`px-2 py-1 rounded font-mono text-xs ${getStatusBadge(
                      game.status
                    )}`}
                  >
                    {game.status.toUpperCase()}
                  </span>
                </div>
                <p className="text-gray-400 font-mono mb-4">
                  {game.description}
                </p>
                <div className="text-sm font-mono text-gray-500">
                  {game.features.join(" • ")}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
