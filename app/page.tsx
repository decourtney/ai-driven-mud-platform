import React from "react";
import SignIn from "./components/sign-in";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 relative overflow-hidden">
      {/* Navigation Bar */}
      <nav className="relative z-10 flex items-center justify-between p-6 bg-gradient-to-b from-black/40 to-transparent backdrop-blur-sm">
        <div className="flex items-center space-x-8">
          {/* Logo */}
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-green-600 flex items-center justify-center font-mono border border-green-400">
              <span className="text-black font-bold text-lg">M</span>
            </div>
            <span className="text-green-400 font-bold text-xl font-mono">
              MudAI
            </span>
          </div>

          {/* Navigation Links */}
          <div className="hidden md:flex space-x-6">
            <button className="text-green-300 hover:text-green-400 transition-colors duration-200 px-3 py-1 font-mono">
              Home
            </button>
            <button className="text-green-300 hover:text-green-400 transition-colors duration-200 px-3 py-1 font-mono">
              News
            </button>
          </div>
        </div>

        {/* Login Button */}
        <SignIn />
      </nav>

      {/* Background Image Placeholder */}
      <div className="absolute inset-0 z-0">
        <div className="w-full h-full bg-gradient-to-br from-slate-900/60 to-black/60 flex items-center justify-center">
          {/* <div className="text-green-400 text-center border-2 border-green-400 p-8 bg-black/50 font-mono">
            <div className="text-lg mb-2">[ BACKGROUND ART PLACEHOLDER ]</div>
            <p className="text-sm text-green-300">
              Your retro game art will display here
            </p>
          </div> */}
        </div>
      </div>

      {/* Main Content */}
      <div className="relative z-10 flex flex-col items-center justify-center min-h-[80vh] text-center px-4">
        {/* Large Logo */}
        <div className="mb-8">
          <div className="w-24 h-24 bg-gradient-to-br from-green-400 to-green-600 flex items-center justify-center shadow-lg font-mono border-2 border-green-400">
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
          <button className="bg-green-600 hover:bg-green-700 text-black text-lg px-8 py-3 font-mono font-bold transition-colors duration-200 border-2 border-green-400">
            [ CONNECT ]
          </button>
          <button className="border-2 border-green-600 text-green-400 hover:bg-green-600/20 text-lg px-8 py-3 font-mono transition-all duration-200">
            [ ABOUT ]
          </button>
        </div>
      </div>
    </div>
  );
}
