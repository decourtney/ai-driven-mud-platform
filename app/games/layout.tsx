import React from "react";
import DropDownMenu from "../components/game/DropDownMenu";
import { auth } from "@/auth";
import { redirect, RedirectType } from "next/navigation";

const GameLayout = async ({ children }: { children: React.ReactNode }) => {
  const session = await auth();
  if (!session) redirect("/signin", RedirectType.replace);

  return (
    <div className="flex flex-col min-h-screen text-white font-mono">
      {/* Header Bar */}
      <div className="bg-gray-900 border-b border-green-500 px-6 py-3 flex justify-between items-center">
        {/* Logo - Top Left */}
        <div className="flex items-center">
          <div className="text-green-400 font-bold text-lg">ADVENTURE</div>
          <div className="text-gray-500 text-sm ml-2">RPG</div>
        </div>

        <DropDownMenu />
      </div>

      {/* Game Content Area */}
      <div className="flex flex-col flex-1 overflow-auto">{children}</div>
    </div>
  );
};

export default GameLayout;
