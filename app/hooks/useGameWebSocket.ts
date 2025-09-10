// hooks/useGameWebSocket.ts
import { useEffect, useRef, useState, useCallback } from "react";
import { ChatMessage, GameMessage, GameState } from "../types/game";

interface UseGameWebSocketProps {
  slug: string;
  sessionId: string;
  userId: string;
  onMessage?: (message: GameMessage) => void;
  onError?: (error: string) => void;
  onConnectionChange?: (connected: boolean) => void;
}

interface UseGameWebSocketReturn {
  isConnected: boolean;
  sendAction: (action: string) => void;
  chatHistory: ChatMessage[];
  gameState: GameState | null;
  lastError: string | null;
  reconnect: () => void;
}

export const useGameWebSocket = ({
  slug,
  sessionId,
  userId,
  onMessage,
  onError,
  onConnectionChange,
}: UseGameWebSocketProps): UseGameWebSocketReturn => {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const [isConnected, setIsConnected] = useState(false);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const MAX_RECONNECT_ATTEMPTS = 5;
  const RECONNECT_DELAY = 1000; // Start with 1 second

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    const wsUrl = `ws://localhost:8000/ws/play/${slug}/${sessionId}/${userId}`;
    console.log("Connecting to:", wsUrl);
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("WebSocket connected");
      setIsConnected(true);
      setLastError(null);
      setReconnectAttempts(0);
      onConnectionChange?.(true);

      // Start ping interval to keep connection alive
      pingIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, 30000); // Ping every 30 seconds
    };

    ws.onclose = (event) => {
      console.log("WebSocket disconnected:", event.code, event.reason);
      setIsConnected(false);
      onConnectionChange?.(false);

      // Clear ping interval
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = null;
      }

      // Attempt reconnection if not manually closed
      if (event.code !== 1000 && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        const delay = RECONNECT_DELAY * Math.pow(2, reconnectAttempts); // Exponential backoff
        console.log(
          `Reconnecting in ${delay}ms... (attempt ${reconnectAttempts + 1})`
        );

        reconnectTimeoutRef.current = setTimeout(() => {
          setReconnectAttempts((prev) => prev + 1);
          connect();
        }, delay);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      const errorMsg = "WebSocket connection error";
      setLastError(errorMsg);
      onError?.(errorMsg);
    };

    ws.onmessage = (event) => {
      try {
        const message: GameMessage = JSON.parse(event.data);
        console.log("Received WebSocket message:", message);

        // Handle different message types
        switch (message.type) {
          case "initial_state":
            console.log("Setting initial game state:", message.data.game_state);
            setGameState(message.data.game_state);
            setChatHistory(message.data.chat_history || []);
            break;

          case "chat_message":
            setChatHistory((prev) => [
              ...prev,
              {
                id: message.data.id,
                speaker: message.data.speaker,
                content: message.data.content,
                timestamp: message.data.timestamp,
              },
            ]);
            break;

          case "action_received":
            // Action was acknowledged by server
            console.log("Action acknowledged:", message.data.action);
            break;

          case "action_result":
            // Action results are typically also sent as chat messages
            // but you might want additional handling here
            console.log("Action result:", message.data);
            break;

          case "game_state_update":
            setGameState((prev) => ({ ...prev, ...message.data }));
            break;

          case "connection_confirmed":
            console.log("Connection confirmed:", message.data);
            break;

          case "error":
            const errorMsg = message.data.message;
            setLastError(errorMsg);
            onError?.(errorMsg);
            break;

          case "pong":
            // Pong received, connection is alive
            break;

          default:
            console.log("Unknown message type:", message.type, message);
        }

        // Call custom message handler
        onMessage?.(message);
      } catch (err) {
        console.error("Failed to parse WebSocket message:", err, event.data);
        setLastError("Failed to parse server message");
      }
    };

    wsRef.current = ws;
  }, [
    slug,
    sessionId,
    userId,
    onMessage,
    onError,
    onConnectionChange,
    reconnectAttempts,
  ]);

  const sendAction = useCallback((action: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const message = {
        type: "player_action",
        data: { action },
        timestamp: new Date().toISOString(),
      };

      console.log("Sending action:", message);
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.error("WebSocket not connected, cannot send action:", action);
      setLastError("Cannot send action: not connected to server");
    }
  }, []);

  const reconnect = useCallback(() => {
    console.log("Manual reconnect requested");

    // Clear any existing reconnection timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close(1000, "Manual reconnect");
    }

    // Reset reconnection attempts and error
    setReconnectAttempts(0);
    setLastError(null);

    // Start new connection
    setTimeout(connect, 100); // Small delay to ensure cleanup
  }, [connect]);

  // Initial connection
  useEffect(() => {
    console.log("Starting WebSocket connection...");
    connect();

    // Cleanup on unmount
    return () => {
      console.log("Cleaning up WebSocket connection...");
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close(1000, "Component unmounting");
      }
    };
  }, [connect]);

  return {
    isConnected,
    sendAction,
    chatHistory,
    gameState,
    lastError,
    reconnect,
  };
};
