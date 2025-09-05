// components/game/GameInterface.tsx
import React, { useState, useRef, useEffect } from "react";
import { Send, Terminal } from "lucide-react";
import { GameMessage, GameInterfaceProps } from "@/app/types/game";

export default function GameInterface({
  onPlayerAction,
  is_processing: isProcessing = false,
}: GameInterfaceProps) {
  const [inputValue, setInputValue] = useState("");
  const [gameMessages, setGameMessages] = useState<GameMessage[]>([
    {
      id: "1",
      type: "scene",
      content:
        "You find yourself standing at the entrance of a dark, foreboding dungeon. Ancient stone walls drip with moisture, and the air carries the musty scent of ages past. Flickering torchlight dances across carved symbols that seem to watch your every move.",
      timestamp: new Date(),
    },
    {
      id: "2",
      type: "system",
      content:
        "Welcome to MudAI! Type your actions to interact with the world.",
      timestamp: new Date(),
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [gameMessages]);

  // Focus input on mount and when not processing
  useEffect(() => {
    if (!isProcessing) {
      inputRef.current?.focus();
    }
  }, [isProcessing]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isProcessing) return;

    const playerMessage: GameMessage = {
      id: Date.now().toString(),
      type: "player",
      content: inputValue.trim(),
      timestamp: new Date(),
      speaker: "You",
    };

    setGameMessages((prev) => [...prev, playerMessage]);

    // Call the parent's action handler
    onPlayerAction?.(inputValue.trim());

    setInputValue("");
  };

  const getMessageStyle = (type: GameMessage["type"]) => {
    switch (type) {
      case "system":
        return "text-green-400 bg-green-400/10 border-l-4 border-green-400 pl-4";
      case "player":
        return "text-cyan-300 bg-cyan-400/5";
      case "npc":
        return "text-yellow-300 bg-yellow-400/5";
      case "scene":
        return "text-purple-300 bg-purple-400/10 border-l-4 border-purple-400 pl-4";
      case "error":
        return "text-red-400 bg-red-400/10 border-l-4 border-red-400 pl-4";
      default:
        return "text-gray-300";
    }
  };

  const formatTimestamp = (timestamp: Date) => {
    return timestamp.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="flex-1 bg-gray-950 flex flex-col">
      {/* Game Header */}
      <div className="bg-gray-800 border-b border-green-500 p-4 flex items-center">
        <Terminal className="text-green-400 mr-3" size={24} />
        <div>
          <h1 className="text-green-400 font-mono font-bold text-xl">
            MudAI Game Terminal
          </h1>
          <p className="text-gray-400 font-mono text-sm">
            Enter commands to interact with the world
          </p>
        </div>
        {isProcessing && (
          <div className="ml-auto flex items-center text-yellow-400 font-mono text-sm">
            <div className="animate-pulse mr-2">●</div>
            Processing...
          </div>
        )}
      </div>

      {/* Messages Display */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
        {gameMessages.map((message) => (
          <div
            key={message.id}
            className={`font-mono text-sm p-3 rounded ${getMessageStyle(
              message.type
            )}`}
          >
            <div className="flex items-start justify-between mb-1">
              <span className="font-bold">
                {message.type === "player" ? "> " : ""}
                {message.speaker && `${message.speaker}: `}
              </span>
              <span className="text-xs text-gray-500 ml-2 flex-shrink-0">
                {formatTimestamp(message.timestamp)}
              </span>
            </div>
            <div className="leading-relaxed">{message.content}</div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-green-500 bg-gray-800 p-4">
        <form onSubmit={handleSubmit} className="flex space-x-3">
          <div className="flex-1 relative">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={
                isProcessing
                  ? "Processing your last action..."
                  : "What do you want to do?"
              }
              disabled={isProcessing}
              className="w-full bg-gray-900 border border-green-500 text-green-400 font-mono px-4 py-3 focus:outline-none focus:border-green-300 disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div className="absolute right-3 top-3 text-green-600 font-mono text-sm">
              &gt;
            </div>
          </div>
          <button
            type="submit"
            disabled={!inputValue.trim() || isProcessing}
            className="bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-black font-mono font-bold px-6 py-3 transition-colors flex items-center"
          >
            <Send size={18} className="mr-2" />
            SEND
          </button>
        </form>

        {/* Command Hints */}
        <div className="mt-2 text-xs font-mono text-gray-500">
          Try: "look around", "attack goblin", "open door", "check inventory"
        </div>
      </div>
    </div>
  );
}
