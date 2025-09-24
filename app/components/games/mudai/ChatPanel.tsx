// WebSocket-enabled ChatPanel.tsx
import React, { useState, useRef, useEffect } from "react";
import { Send, Terminal, Wifi, WifiOff } from "lucide-react";
import { ChatMessage, GameState } from "@/app/types/game";

interface ChatInterface {
  onPlayerAction: (action: string) => void;
  chatHistory: ChatMessage[];
  isConnected: boolean;
  slug: string;
  gameState: GameState;
}

export default function ChatPanel({
  onPlayerAction,
  chatHistory,
  isConnected,
  slug,
  gameState,
}: ChatInterface) {
  const [inputValue, setInputValue] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  // Focus input when connected
  useEffect(() => {
    if (isConnected) {
      inputRef.current?.focus();
    }
  }, [isConnected]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || !isConnected) return;

    // Send action via WebSocket
    onPlayerAction(inputValue.trim());
    setInputValue("");
  };

  const getMessageStyle = (messageType: string) => {
    switch (messageType) {
      case "player":
        return "text-cyan-300 bg-cyan-400/5 border border-cyan-400/20";
      case "narrator":
        return "text-purple-300 bg-purple-400/10 border-l-4 border-purple-400 pl-4";
      case "system":
        return "text-green-400 bg-green-400/10 border-l-4 border-green-400 pl-4";
      case "error":
        return "text-red-400 bg-red-400/10 border-l-4 border-red-400 pl-4";
      default:
        return "text-gray-300";
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const time = new Date(timestamp);
    return time.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getPlaceholder = () => {
    if (!isConnected) {
      return "Connecting to server...";
    }
    return "What do you want to do?";
  };

  const getSenderDisplay = (sender: string) => {
    if (sender === "player") {
      return `> ${sender}`;
    }
    return sender;
  };

  return (
    <div className="flex flex-col w-full bg-gray-950">
      {/* Game Header */}
      <div className=" flex flex-row items-center bg-gray-800 border-b border-green-500 p-4">
        <Terminal className="text-green-400 mr-3" size={24} />
        <div className="flex-1">
          <h1 className="text-green-400 font-mono font-bold text-xl">
            MudAI Game Terminal
          </h1>
          <p className="text-gray-400 font-mono text-sm">
            Real-time WebSocket connection
          </p>
        </div>

        {/* Connection Status */}
        <div className="flex items-center space-x-2">
          {isConnected ? (
            <div className="flex items-center text-green-400 font-mono text-sm">
              <Wifi size={16} className="mr-2" />
              <div className="hidden md:block"> Connected</div>
            </div>
          ) : (
            <div className="flex items-center text-red-400 font-mono text-sm">
              <WifiOff size={16} className="mr-2 animate-pulse" />
              <div className="hidden md:block animate-pulse">Connecting...</div>
            </div>
          )}
        </div>
      </div>

      {/* Messages Display */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
        {chatHistory.map((message, index) => (
          <div
            key={`${message.timestamp}-${index}`}
            className={`font-mono text-sm p-3 rounded transition-all duration-300 ${getMessageStyle(
              message.speaker
            )}`}
          >
            <div className="flex items-start justify-between mb-1">
              <span className="font-bold text-xs uppercase tracking-wide opacity-70">
                {getSenderDisplay(message.speaker)}
              </span>
              <span className="text-xs text-gray-500 ml-2 flex-shrink-0">
                {formatTimestamp(message.timestamp)}
              </span>
            </div>
            <div className="leading-relaxed whitespace-pre-wrap">
              {message.content}
            </div>
          </div>
        ))}

        {/* Show typing indicator or connection status */}
        {!isConnected && chatHistory.length === 0 && (
          <div className="text-center text-gray-500 font-mono p-8">
            <div className="animate-pulse mb-2">Establishing connection...</div>
            <div className="text-xs">
              Please wait while we connect to the game server
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-green-500 bg-gray-800 p-4">
        {/* Enhanced Command Hints */}
        <div className="mb-3 space-y-1">
          <div className="text-xs font-mono text-gray-500">
            {isConnected && !gameState.is_player_input_locked ? (
              <span className="text-green-400 ml-2">Ready for commands</span>
            ) : (
              <span className="text-red-400 animate-pulse">
                Processing...
              </span>
            )}
          </div>
          {!isConnected && (
            <div className="text-xs font-mono text-red-400">
              Connection lost - commands will be sent when reconnected
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="flex space-x-3">
          <div className="flex-1 relative">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={getPlaceholder()}
              disabled={!isConnected || gameState.is_player_input_locked}
              className={`w-full bg-gray-900 border text-green-400 font-mono px-4 py-3 focus:outline-none transition-all duration-200 ${
                !isConnected || gameState.is_player_input_locked
                  ? "border-red-500 opacity-50 cursor-not-allowed"
                  : "border-green-500 focus:border-green-300"
              }`}
            />
            <div className="absolute right-3 top-3 text-green-600 font-mono text-sm">
              &gt;
            </div>
          </div>
          <button
            type="submit"
            disabled={
              !inputValue.trim() ||
              !isConnected ||
              gameState.is_player_input_locked
            }
            className={`font-mono font-bold px-6 py-3 transition-all duration-200 flex items-center ${
              !isConnected || gameState.is_player_input_locked
                ? "bg-gray-600 cursor-not-allowed text-gray-400"
                : "bg-green-600 hover:bg-green-700 text-black"
            }`}
          >
            <Send size={18} className="mr-2" />
            {!isConnected ? "WAIT" : "SEND"}
          </button>
        </form>
      </div>
    </div>
  );
}
