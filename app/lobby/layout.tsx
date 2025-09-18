import React from "react";
import Link from "next/link";
import { auth } from "@/auth";
import Navbar from "@/app/components/NavBar";

interface LobbyLayoutProps {
  children: React.ReactNode;
}

export default async function LobbyLayout({ children }: LobbyLayoutProps) {
  const session = await auth();

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Navigation Bar */}
      <Navbar variant="solid" user={session?.user} />

      {/* Main Content */}
      <main className="relative">{children}</main>

      {/* Footer (Optional) */}
      <footer className="bg-gray-900 border-t border-green-500 mt-12">
        <div className="max-w-6xl mx-auto p-6">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="text-gray-400 font-mono text-sm mb-4 md:mb-0">
              © 2025 MudAI. All rights reserved.
            </div>
            <div className="flex space-x-6 text-sm font-mono">
              <Link
                href="/about"
                className="text-gray-400 hover:text-green-400 transition-colors"
              >
                [ ABOUT ]
              </Link>
              <Link
                href="/help"
                className="text-gray-400 hover:text-green-400 transition-colors"
              >
                [ HELP ]
              </Link>
              <Link
                href="/contact"
                className="text-gray-400 hover:text-green-400 transition-colors"
              >
                [ CONTACT ]
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
