"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { WebSocketMessage } from "../types";

interface Options {
  enabled?: boolean;
  reconnectMs?: number;
  maxReconnectMs?: number;
  heartbeatMs?: number;
  onMessage?: (message: WebSocketMessage) => void;
}

// ✅ NEW: Helper to fix WebSocket URL
function normalizeWsUrl(inputUrl: string): string {
  let url = inputUrl.trim();
  
  // If URL doesn't contain /ws, add it
  if (!url.includes('/ws')) {
    // Remove trailing slash if exists
    url = url.replace(/\/$/, '');
    // Add /ws
    url = `${url}/ws`;
  }
  
  return url;
}

export function useWebSocket(url: string, options: Options = {}) {
  const {
    enabled = true,
    reconnectMs = 1500,
    maxReconnectMs = 10000,
    heartbeatMs = 20000,
    onMessage,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const heartbeatTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const intentionalCloseRef = useRef(false);
  const onMessageRef = useRef(onMessage);
  const attemptRef = useRef(0);

  // ✅ FIXED: Normalize URL before use
  const normalizedUrl = normalizeWsUrl(url);

  useEffect(() => { 
    onMessageRef.current = onMessage; 
  }, [onMessage]);

  useEffect(() => {
    console.log(`🔧 WebSocket normalized URL: ${normalizedUrl} (original: ${url})`);
  }, [normalizedUrl, url]);

  const clearTimers = useCallback(() => {
    if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
    if (heartbeatTimerRef.current) clearInterval(heartbeatTimerRef.current);
    reconnectTimerRef.current = null;
    heartbeatTimerRef.current = null;
  }, []);

  const disconnect = useCallback(() => {
    intentionalCloseRef.current = true;
    clearTimers();
    try { socketRef.current?.close(1000, "Client disconnect"); } catch {}
    socketRef.current = null;
    setIsConnected(false);
  }, [clearTimers]);

  const connect = useCallback(() => {
    if (!enabled || typeof window === "undefined") return;

    clearTimers();
    intentionalCloseRef.current = false;

    console.log(`🔌 Connecting WebSocket to: ${normalizedUrl}`);

    const socket = new WebSocket(normalizedUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      attemptRef.current = 0;
      setReconnectAttempt(0);
      setIsConnected(true);
      console.log(`✅ WebSocket connected to: ${normalizedUrl}`);

      heartbeatTimerRef.current = setInterval(() => {
        if (socket.readyState !== WebSocket.OPEN) return;
        socket.send(JSON.stringify({
          type: "heartbeat",
          data: { client_time: new Date().toISOString() },
        }));
      }, heartbeatMs);
    };

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as WebSocketMessage;
        if (message.type === "heartbeat_ack") {
          return;
        }
        setLastMessage(message);
        onMessageRef.current?.(message);
      } catch {
        console.warn("[WS] Ignored malformed server message");
      }
    };

    socket.onerror = (error) => {
      console.error(`❌ WebSocket error:`, error);
      try { socket.close(); } catch {}
    };

    socket.onclose = (event) => {
      clearTimers();
      setIsConnected(false);
      if (socketRef.current === socket) socketRef.current = null;

      console.log(`🔌 WebSocket closed (code: ${event.code})`);

      if (intentionalCloseRef.current || !enabled) return;

      attemptRef.current += 1;
      setReconnectAttempt(attemptRef.current);
      const delay = Math.min(
        maxReconnectMs,
        reconnectMs * 2 ** Math.min(attemptRef.current - 1, 5),
      );
      console.log(`🔄 Reconnecting in ${delay}ms (attempt ${attemptRef.current})`);
      reconnectTimerRef.current = setTimeout(connect, delay);
    };
  }, [clearTimers, enabled, heartbeatMs, maxReconnectMs, reconnectMs, normalizedUrl]);

  useEffect(() => {
    if (!enabled) return;
    connect();
    return () => {
      intentionalCloseRef.current = true;
      clearTimers();
      try { socketRef.current?.close(1000, "Component unmounted"); } catch {}
      socketRef.current = null;
      setIsConnected(false);
    };
  }, [connect, clearTimers, enabled]);

  useEffect(() => {
    if (!enabled || typeof document === "undefined") return;

    const onVisible = () => {
      if (document.visibilityState !== "visible") return;
      const socket = socketRef.current;
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
          type: "heartbeat",
          data: { client_time: new Date().toISOString(), reason: "tab_focus" },
        }));
      } else if (!intentionalCloseRef.current) {
        connect();
      }
    };

    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, [enabled, connect]);

  const sendMessage = useCallback((message: unknown) => {
    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) return false;
    socket.send(JSON.stringify(message));
    return true;
  }, []);

  return { isConnected, lastMessage, reconnectAttempt, sendMessage, disconnect, connect };
}