import React from "react";
import Link from "next/link";
import { Play } from "lucide-react";
import { auth } from "@/auth";
import Navbar from "@/components/NavBar";

export default async function LandingPage() {
  const session = await auth();

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Navigation Bar */}
      <Navbar variant="transparent" user={session?.user} />

      {/* Main Content */}
      <div className="relative flex flex-col items-center justify-center min-h-[85vh] text-center px-4">
        {/* Large Logo */}
        <div className="mb-8">
          <div className="w-24 h-24 bg-gradient-to-br from-green-400 to-green-600 flex items-center justify-center shadow-lg shadow-green-500/20 font-mono border-2 border-green-400">
            <span className="text-black font-bold text-4xl">M</span>
          </div>
        </div>

        {/* Game Title */}
        <h1 className="text-6xl md:text-7xl font-bold text-green-400 mb-6 font-mono tracking-wider">
          MudAI
        </h1>

        {/* Catchphrase */}
        <p className="text-lg text-green-300 mb-12 font-mono">
          &gt; Enter the AI-powered text realm
        </p>

        {/* Call to Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-4">
          <Link href="/lobby">
            <button className="bg-green-600 hover:bg-green-700 text-black text-lg px-8 py-3 font-mono font-bold transition-colors duration-200 border-2 border-green-400 flex items-center">
              <Play size={20} className="mr-3" />[ PLAY ]
            </button>
          </Link>
          <button className="border-2 border-green-600 text-green-400 hover:bg-green-600/20 text-lg px-8 py-3 font-mono transition-all duration-200">
            [ ABOUT ]
          </button>
        </div>

        {/* Additional Terminal-style Elements */}
        <div className="mt-16 max-w-2xl">
          <div className="bg-gray-900 border border-green-500 rounded p-6 text-left">
            <div className="text-green-400 font-mono text-sm mb-3">
              system@mudai:~$ cat welcome.txt
            </div>
            <div className="text-gray-300 font-mono text-sm leading-relaxed">
              Welcome to MudAI - where classic text-based adventure meets
              cutting-edge AI.
              <br />
              Every decision shapes your story. Every world is unique.
              <br />
              <span className="text-green-300">
                Ready to begin your adventure?
              </span>
            </div>
            <div className="text-green-400 font-mono text-sm mt-3">
              system@mudai:~$ <span className="animate-pulse">_</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
