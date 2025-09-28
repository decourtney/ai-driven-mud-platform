"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import {
  CharacterState,
  ChatMessage,
  GameMessage,
  GameState,
} from "../types/game";
import { useSession } from "next-auth/react";

interface UseGameWebSocketProps {
  slug: string;
  sessionId: string;
  onMessage?: (message: GameMessage) => void;
  onError?: (error: string) => void;
  onConnectionChange?: (connected: boolean) => void;
}

interface UseGameWebSocketReturn {
  isConnected: boolean;
  sendAction: (action: string) => void;
  chatHistory: ChatMessage[];
  gameState: GameState | null;
  playerState: CharacterState | null;
  lastError: string | null;
  reconnect: () => void;
}

export const useGameWebSocket = ({
  slug,
  sessionId,
  onMessage,
  onError,
  onConnectionChange,
}: UseGameWebSocketProps): UseGameWebSocketReturn => {
  const { data: session, status } = useSession();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const mountedRef = useRef(true);
  const connectingRef = useRef(false);

  const [isConnected, setIsConnected] = useState(false);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>(
    [] as ChatMessage[]
  );
  const [gameState, setGameState] = useState<GameState>({} as GameState);
  const [playerState, setPlayerState] = useState<CharacterState>(
    {} as CharacterState
  );
  const [lastError, setLastError] = useState<string | null>(null);

  const MAX_RECONNECT_ATTEMPTS = 5;
  const RECONNECT_DELAY = 1000;

  const cleanup = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }

    if (wsRef.current) {
      const ws = wsRef.current;
      wsRef.current = null;

      if (
        ws.readyState === WebSocket.OPEN ||
        ws.readyState === WebSocket.CONNECTING
      ) {
        ws.close(1000, "Cleanup");
      }
    }

    connectingRef.current = false;
  }, []);

  const connect = useCallback(() => {
    if (!mountedRef.current || !session?.user?.id || connectingRef.current) {
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    connectingRef.current = true;

    // Close existing connection first
    if (wsRef.current) {
      const oldWs = wsRef.current;
      wsRef.current = null;
      if (
        oldWs.readyState === WebSocket.OPEN ||
        oldWs.readyState === WebSocket.CONNECTING
      ) {
        oldWs.close(1000, "Reconnecting");
      }
    }

    const userId = session.user.id;
    const wsUrl = `ws://localhost:8000/ws/play/${slug}/${sessionId}/${userId}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      if (!mountedRef.current) {
        ws.close(1000, "Component unmounted");
        return;
      }

      connectingRef.current = false;
      setIsConnected(true);
      setLastError(null);
      reconnectAttemptsRef.current = 0;
      onConnectionChange?.(true);

      pingIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN && mountedRef.current) {
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, 30000);
    };

    ws.onclose = (event) => {
      connectingRef.current = false;

      if (!mountedRef.current) {
        return;
      }

      setIsConnected(false);
      onConnectionChange?.(false);

      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = null;
      }

      if (
        event.code !== 1000 &&
        reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS &&
        mountedRef.current
      ) {
        const delay =
          RECONNECT_DELAY * Math.pow(2, reconnectAttemptsRef.current);

        reconnectTimeoutRef.current = setTimeout(() => {
          if (mountedRef.current && !connectingRef.current) {
            reconnectAttemptsRef.current++;
            connect();
          }
        }, delay);
      }
    };

    ws.onerror = (err) => {
      connectingRef.current = false;

      const msg = "WebSocket connection error";
      if (mountedRef.current) {
        setLastError(msg);
        onError?.(msg);
      }
    };

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;

      try {
        const message: GameMessage = JSON.parse(event.data);

        switch (message.type) {
          case "connection_confirmed":
            break;
          case "initial_state":
            setGameState((prev) => ({ ...prev, ...message.data.game_state }));
            setPlayerState((prev) => ({
              ...prev,
              ...message.data.player_state,
            }));
            setChatHistory(message.data.chat_history);
            break;
          case "lock_player_input":
            setGameState((prev) => ({
              ...prev,
              is_player_input_locked: message.data.is_locked,
            }));
            break;
          case "chat_message":
            setChatHistory((prev) => [...prev, message.data]);
            break;
          case "session_state_update":
            setGameState((prev) => ({ ...prev, ...message.data.game_state }));
            setPlayerState((prev) => ({
              ...prev,
              ...message.data.player_state,
            }));
            break;
          case "action_result":
            setChatHistory((prev) => [...prev, message.data.narration]);
            setPlayerState((prev) => ({
              ...prev,
              ...message.data.player_state,
            }));
            break;

          case "streaming_message":
            setChatHistory((prev) => {
              const messageId = message.data.narration.id;
              const idx = prev.findIndex((msg) => msg.id === messageId);

              if (idx !== -1) {
                // Update existing
                const updated = [...prev];
                const updatedMessage = {
                  ...updated[idx],
                  content: message.data.narration.content,
                  timestamp: message.data.timestamp || new Date().toISOString(),
                  typing: message.data.narration.typing,
                };
                updated[idx] = updatedMessage;
                return updated;
              } else {
                // Create new
                const newMessage = {
                  id: messageId,
                  speaker: message.data.speaker || "narrator",
                  content: message.data.narration.content,
                  timestamp: message.data.timestamp || new Date().toISOString(),
                  typing: message.data.narration.typing,
                };
                const newHistory = [...prev, newMessage];
                return newHistory;
              }
            });
            break;

          case "error":
            setLastError(message.data.message);
            onError?.(message.data.message);
            break;
          case "pong":
            break;
        }

        onMessage?.(message);
      } catch (err) {
        if (mountedRef.current) {
          setLastError("Failed to parse server message");
        }
      }
    };

    wsRef.current = ws;
  }, [
    slug,
    sessionId,
    session?.user?.id,
    onMessage,
    onError,
    onConnectionChange,
  ]);

  const sendAction = useCallback(
    (action: string) => {
      if (gameState.is_player_input_locked) {
        setLastError("Cannot send action: input is currently locked");
        return;
      }

      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({
            type: "player_action",
            data: { action },
            timestamp: new Date().toISOString(),
          })
        );
      } else {
        setLastError("Cannot send action: not connected");
      }
    },
    [gameState.is_player_input_locked]
  );

  const reconnect = useCallback(() => {
    cleanup();
    reconnectAttemptsRef.current = 0;
    setLastError(null);

    setTimeout(() => {
      if (mountedRef.current) {
        connect();
      }
    }, 100);
  }, [connect, cleanup]);

  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;
      cleanup();
    };
  }, []);

  useEffect(() => {
    if (status === "authenticated" && session?.user?.id) {
      const connectTimeout = setTimeout(() => {
        if (mountedRef.current) {
          connect();
        }
      }, 100);

      return () => clearTimeout(connectTimeout);
    }
  }, [status, session?.user?.id, slug, sessionId]);

  return {
    isConnected,
    sendAction,
    chatHistory,
    gameState,
    playerState,
    lastError,
    reconnect,
  };
};
