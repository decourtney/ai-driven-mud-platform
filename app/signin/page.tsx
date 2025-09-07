import React from "react";
import Link from "next/link";
import { Github, Chrome, ArrowLeft } from "lucide-react";
import { signIn } from "@/auth";
import Navbar from "@/app/components/NavBar";

export default function SignIn() {
  return (
    <div className="min-h-screen bg-black text-white">
      {/* Navigation Bar */}
      <Navbar variant="solid" />

      {/* Main Content */}
      <div className="relative z-10 flex flex-col items-center justify-center min-h-[85vh] px-4">
        <div className="w-full max-w-md">
          {/* Back Link */}
          <Link
            href="/lobby"
            className="inline-flex items-center text-green-400 hover:text-green-300 font-mono text-sm mb-8 transition-colors"
          >
            <ArrowLeft size={16} className="mr-2" />[ BACK TO THE LOBBY ]
          </Link>

          {/* Header */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-gradient-to-br from-green-400 to-green-600 flex items-center justify-center shadow-lg shadow-green-500/20 font-mono border-2 border-green-400 mx-auto mb-6">
              <span className="text-black font-bold text-2xl">M</span>
            </div>
            <h1 className="text-3xl font-bold text-green-400 mb-2 font-mono">
              ACCESS TERMINAL
            </h1>
            <p className="text-green-300 font-mono text-sm">
              &gt; Authentication required to proceed
            </p>
          </div>

          {/* Terminal-style Login Box */}
          <div className="bg-gray-900 border-2 border-green-500 rounded-lg overflow-hidden">
            {/* Terminal Header */}
            <div className="bg-gray-800 px-4 py-2 border-b border-green-500">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <span className="text-green-400 font-mono text-xs ml-4">
                  auth@mudai.terminal
                </span>
              </div>
            </div>

            {/* Login Content */}
            <div className="p-8">
              <div className="text-green-400 font-mono text-sm mb-6">
                <div>system@mudai:~$ initialize_auth</div>
                <div className="text-gray-300 mt-2">
                  Select authentication method:
                </div>
              </div>

              {/* OAuth Buttons */}
              <div className="space-y-4">
                {/* GitHub OAuth */}
                <form
                  action={async () => {
                    "use server";
                    await signIn("github", { redirectTo: "/lobby" });
                  }}
                >
                  <button
                    type="submit"
                    className="w-full bg-gray-800 hover:bg-gray-700 border-2 border-green-600 hover:border-green-400 text-green-300 font-mono p-4 transition-all duration-200 flex items-center justify-center group"
                  >
                    <Github
                      size={20}
                      className="mr-3 group-hover:text-green-400 transition-colors"
                    />
                    [ AUTHENTICATE VIA GITHUB ]
                  </button>
                </form>

                {/* Google OAuth */}
                <form
                  action={async () => {
                    "use server";
                    await signIn("google", { redirectTo: "/lobby" });
                  }}
                >
                  <button
                    type="submit"
                    className="w-full bg-gray-800 hover:bg-gray-700 border-2 border-green-600 hover:border-green-400 text-green-300 font-mono p-4 transition-all duration-200 flex items-center justify-center group"
                  >
                    <Chrome
                      size={20}
                      className="mr-3 group-hover:text-green-400 transition-colors"
                    />
                    [ AUTHENTICATE VIA GOOGLE ]
                  </button>
                </form>
              </div>

              {/* Terminal Output */}
              <div className="mt-8 bg-black border border-green-500 rounded p-4">
                <div className="text-green-400 font-mono text-xs">
                  <div className="mb-1">
                    &gt; status: waiting for authentication...
                  </div>
                  <div className="text-gray-400 mb-1">
                    &gt; secure connection established
                  </div>
                  <div className="text-gray-400 mb-1">
                    &gt; oauth providers loaded
                  </div>
                  <div className="flex items-center">
                    <span className="text-green-300">&gt; ready:</span>
                    <span className="ml-2 animate-pulse">_</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Footer Info */}
          <div className="mt-8 text-center">
            <div className="bg-gray-900/50 border border-green-500/30 rounded p-4">
              <p className="text-gray-400 font-mono text-xs mb-2">
                &gt; First time? No worries - OAuth will create your account
                automatically
              </p>
              <p className="text-gray-400 font-mono text-xs">
                &gt; Your data is encrypted and secure
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
