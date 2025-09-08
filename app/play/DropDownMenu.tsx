"use client";

import { Power } from "lucide-react";
import Link from "next/link";
import { useParams, usePathname, useRouter } from "next/navigation";
import React, { useEffect, useRef, useState } from "react";

export default function DropDownMenu() {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const params = useParams();
  const pathname = usePathname();

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsDropdownOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  useEffect(() => {
    setIsDropdownOpen(false);
  }, [pathname]);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsDropdownOpen(!isDropdownOpen)}
        className="bg-orange-600 hover:bg-orange-700 text-white p-2 transition-colors border border-orange-500 hover:border-orange-400 rounded flex items-center gap-1"
        title="Save and Exit Options"
      >
        <Power size={12} />
      </button>

      {/* Dropdown Menu */}
      {isDropdownOpen && (
        <div className="absolute right-0 mt-1 w-32 bg-gray-800 border border-green-500 rounded shadow-lg">
          <Link href={`/play/${params.slug}`}>
            <div className="w-full hover:bg-green-700/60 text-green-400 hover:text-green-200 active:bg-green-600/60 font-bold px-3 py-2 transition-all duration-200 border-b border-green-500 flex items-center gap-3">
              Main Menu
            </div>
          </Link>
          <Link href={`/lobby`}>
            <div className="w-full hover:bg-green-700/60 text-green-400 hover:text-green-200 active:bg-green-600/60 font-bold px-3 py-2 transition-all duration-200 border-b border-green-500 flex items-center gap-3">
              Lobby
            </div>
          </Link>
        </div>
      )}
    </div>
  );
}
