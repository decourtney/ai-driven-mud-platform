import React from "react";
import DropDownMenu from "./DropDownMenu";
import { auth } from "@/auth";
import { redirect, RedirectType } from "next/navigation";

export default async function GameLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await auth();
  if (!session) redirect("/signin", RedirectType.replace);

  return (
    <div className="flex flex-col min-h-screen text-white font-mono">
      {/* Background Image */}
      <div className="absolute inset-0 w-full h-full -z-20">
        <img
          src="/images/mudai.jpeg"
          alt="Fantasy adventure scene with mystical landscape"
          className="w-full h-full object-cover"
          style={{
            filter: "contrast(1.1) brightness(0.5) sepia(0.5) saturate(0.7)",
          }}
        />

        {/* Gradient overlay from left */}
        <div className="absolute inset-0 bg-gradient-to-r from-black/80 via-black/20 to-transparent"></div>
      </div>

      {/* Header Bar */}
      <div className="bg-gray-900/80 backdrop-blur-md border-b border-green-500 px-6 py-3 flex justify-between items-center z-10">
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
}
