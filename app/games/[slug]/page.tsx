"use client";

import React, { useState, useEffect } from "react";
import { Play, Plus, Settings, Book, Minus } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { toast } from "sonner";

interface MainMenuProps {
  userId: string;
}

const MainMenu = ({ userId }: MainMenuProps) => {
  const [hasExistingSession, setHasExistingSession] = useState<string | null>();
  const params = useParams();

  // Check for existing game session on component mount
  useEffect(() => {
    const checkForSession = async () => {
      try {
        const res = await fetch(`/api/sessions/${params.slug}/status`, {
          method: "GET",
          headers: { "Content-Type": "application/json" },
        });

        if (!res.ok) {
          const errorText = await res.text();
          throw new Error(errorText);
        }

        const data = await res.json();
        console.log("Existing session data:", data);
        setHasExistingSession(data.session_id);
      } catch (err: any) {
        toast.error(err.message || "Something went wrong");
      }
    };

    checkForSession();
  }, [params.slug]);

  const handleContinueGame = () => {
    console.log("Continue existing game session");
    // Navigate to game or load existing character
  };

  const handleNewGame = () => {
    console.log("Start new game - navigate to character creation");
    // Navigate to character creation
  };

  const handleCredits = () => {
    console.log("Show credits/about");
  };

  const handleDelete = async () => {
    try {
      const res = await fetch(`/api/sessions/${params.slug}`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(hasExistingSession),
      });

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(errorText);
      }

      const data = await res.json();
      console.log("Existing session data:", data);
      setHasExistingSession(data.session_id);
    } catch (err: any) {
      toast.error(err.message || "Something went wrong");
    }
  };

  return (
    <div className="min-h-screen bg-black text-white font-mono relative overflow-hidden">
      {/* Background Image */}
      <div className="absolute inset-0 w-full h-full">
        <img
          src="/images/main-menu-bg.webp"
          alt="Fantasy adventure scene with mystical landscape"
          className="w-full h-full object-cover"
          style={{
            filter: "contrast(1.1) brightness(0.8) sepia(0.1) saturate(0.7)",
          }}
        />
        {/* Dark overlay for readability */}
        <div className="absolute inset-0 bg-black/40"></div>
        {/* Gradient overlay from left */}
        <div className="absolute inset-0 bg-gradient-to-r from-black/80 via-black/20 to-transparent"></div>
      </div>

      {/* Content */}
      <div className="relative z-10 flex flex-col h-screen max-w-7xl mx-auto">
        {/* Title Area */}
        <div className="pt-12 px-8">
          <h1 className="text-6xl font-bold text-green-400 mb-4 tracking-wider">
            MudAI
          </h1>
        </div>

        {/* Menu Buttons - Top Left Area */}
        <div className="px-8 space-y-4 max-w-sm">
          {/* Continue Game Button - only show if session exists */}
          {hasExistingSession && (
            <Link
              href={`${params.slug}`}
              className="w-full bg-green-700/60 backdrop-blur-sm hover:bg-green-700/60 text-green-400 hover:text-green-200 active:bg-green-600/60 font-bold py-4 px-6 transition-all duration-200 border-2 border-green-500 active:border-green-300 flex items-center gap-3"
            >
              <Play size={20} />
              <div className="text-left">
                <div className="text-lg">CONTINUE ADVENTURE</div>
                <div className="text-sm opacity-80">Resume your journey</div>
              </div>
            </Link>
          )}

          {/* Start New Game Button */}
          <Link
            href={`${params.slug}/create`}
            className="w-full bg-black/60 backdrop-blur-sm hover:bg-green-700/60 text-green-400 hover:text-green-200 active:bg-green-600/60 font-bold py-4 px-6 transition-all duration-200 border-2 border-green-500 active:border-green-300 flex items-center gap-3"
          >
            <Plus size={20} />
            <div className="text-left">
              <div className="text-lg">START NEW ADVENTURE</div>
              <div className="text-sm opacity-80">Create a new character</div>
            </div>
          </Link>

          {/* Credits/About Button */}
          <button
            onClick={handleCredits}
            className="w-full bg-black/60 backdrop-blur-sm hover:bg-green-700/60 text-green-400 hover:text-green-200 active:bg-green-600/60 font-bold py-4 px-6 transition-all duration-200 border-2 border-green-500 active:border-green-300 flex items-center gap-3"
          >
            <Book size={18} />
            <span className="text-lg">CREDITS</span>
          </button>

          {/* Delete Current Game */}
          {hasExistingSession && (
            <button
              onClick={handleDelete}
              className="w-full bg-black/60 backdrop-blur-sm hover:bg-red-700/60 text-red-500 hover:text-green-200 active:bg-red-600/60 font-bold py-4 px-6 transition-all duration-200 border-2 border-red-500 active:border-red-300 flex items-center gap-3"
            >
              <Minus size={20} />
              <div className="text-left">
                <div className="text-lg">DELETE ADVENTURE</div>
              </div>
            </button>
          )}
        </div>
      </div>

      {/* Decorative elements */}
      <div className="absolute bottom-4 right-4 text-xs text-gray-600 font-mono">
        [ PRESS ANY BUTTON TO BEGIN ]
      </div>
    </div>
  );
};

export default MainMenu;
