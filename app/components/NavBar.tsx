// components/Navbar.tsx
"use client";
import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { Play, User, LogOut, UserCircle } from "lucide-react";
import { signOut } from "next-auth/react";

interface NavbarProps {
  variant?: "solid" | "transparent";
  user?: {
    name?: string | null;
    email?: string | null;
    image?: string | null;
  } | null;
}

export default function Navbar({ variant = "solid", user }: NavbarProps) {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const isLoggedIn = !!user;

  // Close dropdown when clicking outside
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

  const handleSignOut = async () => {
    setIsDropdownOpen(false);
    await signOut({ callbackUrl: "/" });
  };

  const navbarClasses =
    variant === "transparent"
      ? "bg-gradient-to-b from-gray-900 to-transparent border-b border-green-500/50 backdrop-blur-sm"
      : "bg-gray-900 border-b border-green-500";

  return (
    <nav className={`${navbarClasses} relative z-10`}>
      <div className="max-w-6xl mx-auto flex items-center justify-between p-4">
        {/* Left Side - Logo and Navigation */}
        <div className="flex items-center space-x-8">
          {/* Logo */}
          <Link href="/" className="flex items-center space-x-3 group">
            <div className="w-8 h-8 bg-green-600 flex items-center justify-center font-mono border border-green-400 group-hover:bg-green-700 transition-colors">
              <span className="text-black font-bold text-lg">M</span>
            </div>
            <span className="text-green-400 font-bold text-xl font-mono group-hover:text-green-300 transition-colors">
              MudAI
            </span>
          </Link>

          {/* Navigation Links */}
          <div className="hidden md:flex space-x-6">
            <Link href="/lobby">
              <button className="text-green-300 hover:text-green-400 transition-colors duration-200 px-3 py-2 font-mono border border-transparent hover:border-green-400">
                [ HOME ]
              </button>
            </Link>
            <Link href="/lobby/news">
              <button className="text-green-300 hover:text-green-400 transition-colors duration-200 px-3 py-2 font-mono border border-transparent hover:border-green-400">
                [ NEWS ]
              </button>
            </Link>
          </div>
        </div>

        {/* Right Side - Play Button and User Icon */}
        <div className="flex items-center space-x-4">
          {/* Play Button */}
          <Link href="/lobby">
            <button className="bg-green-600 hover:bg-green-700 text-black font-mono font-bold px-6 py-2 transition-colors duration-200 border-2 border-green-400 flex items-center">
              <Play size={16} className="mr-2" />[ PLAY ]
            </button>
          </Link>

          {/* User Icon with Dropdown */}
          <div className="relative" ref={dropdownRef}>
            {isLoggedIn ? (
              <>
                <button
                  onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                  className="w-10 h-10 bg-gray-800 border-2 border-green-500 hover:border-green-400 flex items-center justify-center transition-colors duration-200 cursor-pointer group relative"
                >
                  {user?.image ? (
                    <img
                      src={user.image}
                      alt={user.name || "User"}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <User
                      size={20}
                      className="text-green-400 group-hover:text-green-300 transition-colors"
                    />
                  )}
                </button>

                {/* Dropdown Menu */}
                {isDropdownOpen && (
                  <div className="absolute right-0 top-full mt-2 w-64 bg-gray-900 border-2 border-green-500 shadow-lg shadow-green-500/10 z-50">
                    {/* User Info Section */}
                    <div className="p-4 border-b border-green-500/30">
                      <div className="flex items-center space-x-3">
                        <div className="w-12 h-12 bg-gray-800 border-2 border-green-400 flex items-center justify-center">
                          {user?.image ? (
                            <img
                              src={user.image}
                              alt={user.name || "User"}
                              className="w-full h-full object-cover"
                            />
                          ) : (
                            <UserCircle size={24} className="text-green-400" />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-green-300 font-mono font-bold text-sm truncate">
                            {user?.name || "User"}
                          </div>
                          <div className="text-gray-400 font-mono text-xs truncate">
                            {user?.email}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Menu Items */}
                    <div className="py-2">
                      <Link href="/profile">
                        <button
                          onClick={() => setIsDropdownOpen(false)}
                          className="w-full text-left px-4 py-3 text-green-300 hover:bg-gray-800 hover:text-green-400 transition-colors font-mono text-sm flex items-center"
                        >
                          <UserCircle size={16} className="mr-3" />[ PROFILE ]
                        </button>
                      </Link>

                      <button
                        onClick={handleSignOut}
                        className="w-full text-left px-4 py-3 text-green-300 hover:bg-gray-800 hover:text-red-400 transition-colors font-mono text-sm flex items-center"
                      >
                        <LogOut size={16} className="mr-3" />[ SIGN OUT ]
                      </button>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <Link href="/signin">
                <div className="w-10 h-10 bg-gray-800 border-2 border-green-500 hover:border-green-400 flex items-center justify-center transition-colors duration-200 cursor-pointer group">
                  <User
                    size={20}
                    className="text-green-400 group-hover:text-green-300 transition-colors"
                  />
                </div>
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* Mobile Menu Toggle (for future implementation) */}
      <div className="md:hidden absolute right-4 top-4">
        <button className="text-green-400 hover:text-green-300 transition-colors">
          <div className="w-6 h-6 flex flex-col justify-center space-y-1">
            <div className="h-0.5 bg-current"></div>
            <div className="h-0.5 bg-current"></div>
            <div className="h-0.5 bg-current"></div>
          </div>
        </button>
      </div>
    </nav>
  );
}
