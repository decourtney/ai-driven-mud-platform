// Fixed ChatInterface.tsx with scene and npcs support
import React, { useState, useRef, useEffect } from "react";
import { Send, Terminal, Brain } from "lucide-react";
import {
  GameMessage,
  GameInterfaceProps,
  CharacterState,
} from "@/app/types/game";
import { NpcsState, SceneState } from "./GamePage";

interface EnhancedGameInterfaceProps extends GameInterfaceProps {
  scene: SceneState;
  npcs: CharacterState[];
}

export default function ChatInterface({
  onPlayerAction,
  is_processing: isProcessing = false,
  scene,
  npcs,
}: EnhancedGameInterfaceProps) {
  const [inputValue, setInputValue] = useState("");
  const [gameMessages, setGameMessages] = useState<GameMessage[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Initialize messages with scene description on mount
  useEffect(() => {
    if (gameMessages.length === 0) {
      const initialMessages: GameMessage[] = [];

      if (scene) {
        initialMessages.push({
          id: "scene-intro",
          type: "scene",
          content: `${scene.title}: ${scene.description}`,
          timestamp: new Date(),
        });
      } else {
        initialMessages.push({
          id: "1",
          type: "scene",
          content:
            "You find yourself in a mysterious location, ready for adventure.",
          timestamp: new Date(),
        });
      }

      initialMessages.push({
        id: "system-welcome",
        type: "system",
        content:
          "Welcome to MudAI! Type your actions to interact with the world.",
        timestamp: new Date(),
      });

      setGameMessages(initialMessages);
    }
  }, [scene]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [gameMessages]);

  // Focus input when not processing
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
        return "text-cyan-300 bg-cyan-400/5 border border-cyan-400/20";
      case "npc":
        return "text-yellow-300 bg-yellow-400/5 border border-yellow-400/20";
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

  const getPlaceholder = () => {
    if (isProcessing) {
      return "Processing your action...";
    }
    return "What do you want to do?";
  };

  return (
    <div className="flex flex-col w-full bg-gray-950">
      {/* Game Header */}
      <div className="bg-gray-800 border-b border-green-500 p-4 flex items-center">
        <Terminal className="text-green-400 mr-3" size={24} />
        <div className="flex-1">
          <h1 className="text-green-400 font-mono font-bold text-xl">
            MudAI Game Terminal
          </h1>
          <p className="text-gray-400 font-mono text-sm">
            Enter commands to interact with the world
          </p>
        </div>

        {/* Processing Indicator */}
        {isProcessing && (
          <div className="flex items-center space-x-2">
            <div className="text-yellow-400 font-mono text-sm flex items-center">
              <div className="animate-pulse mr-2">●</div>
              Processing your action...
            </div>
          </div>
        )}
      </div>

      {/* Messages Display */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
        {gameMessages.map((message) => (
          <div
            key={message.id}
            className={`font-mono text-sm p-3 rounded transition-all duration-300 ${getMessageStyle(
              message.type
            )}`}
          >
            <div className="flex items-start justify-between mb-1">
              <span className="font-bold text-xs uppercase tracking-wide opacity-70">
                {message.type === "player" && "> "}
                {message.speaker && `${message.speaker}: `}
                {!message.speaker &&
                  message.type !== "player" &&
                  `${message.type}: `}
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
              placeholder={getPlaceholder()}
              disabled={isProcessing}
              className={`w-full bg-gray-900 border text-green-400 font-mono px-4 py-3 focus:outline-none transition-all duration-200 ${
                isProcessing
                  ? "border-yellow-500 opacity-50 cursor-not-allowed"
                  : "border-green-500 focus:border-green-300"
              }`}
            />
            <div className="absolute right-3 top-3 text-green-600 font-mono text-sm">
              &gt;
            </div>
          </div>
          <button
            type="submit"
            disabled={!inputValue.trim() || isProcessing}
            className={`font-mono font-bold px-6 py-3 transition-all duration-200 flex items-center ${
              isProcessing
                ? "bg-gray-600 cursor-not-allowed text-gray-400"
                : "bg-green-600 hover:bg-green-700 text-black"
            }`}
          >
            <Send size={18} className="mr-2" />
            {isProcessing ? "WAIT" : "SEND"}
          </button>
        </form>

        {/* Enhanced Command Hints */}
        <div className="mt-3 space-y-1">
          <div className="text-xs font-mono text-gray-500">
            Try: "look around", "attack goblin", "open door", "check inventory"
            {npcs && npcs.length > 0 && (
              <span className="text-yellow-400 ml-2">
                | NPCs present: {npcs.map((npc) => npc.name).join(", ")}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
