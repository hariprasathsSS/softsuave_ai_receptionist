import { useState, useEffect, useRef, useCallback } from "react";

type ReadyStateLabel = "connecting" | "open" | "closing" | "closed";

function getReadyStateLabel(rs: number): ReadyStateLabel {
  switch (rs) {
    case WebSocket.CONNECTING:
      return "connecting";
    case WebSocket.OPEN:
      return "open";
    case WebSocket.CLOSING:
      return "closing";
    default:
      return "closed";
  }
}

interface UseWebSocketOptions {
  onMessage?: (data: any) => void;
  reconnect?: boolean;
  maxReconnectAttempts?: number;
}

export function useWebSocket(url: string | null, options: UseWebSocketOptions = {}) {
  const { onMessage, reconnect = true, maxReconnectAttempts = 5 } = options;

  const [lastMessage, setLastMessage] = useState<string | null>(null);
  const [lastJsonMessage, setLastJsonMessage] = useState<any>(null);
  const [messageHistory, setMessageHistory] = useState<any[]>([]);
  const [readyState, setReadyState] = useState<number>(WebSocket.CLOSED);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;
  const closingRef = useRef(false);

  const connect = useCallback(() => {
    if (!url) return;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setReadyState(WebSocket.OPEN);
      reconnectCountRef.current = 0;
    };

    ws.onclose = () => {
      setReadyState(WebSocket.CLOSED);
      if (closingRef.current) return;
      // Auto-reconnect with exponential backoff
      if (reconnect && reconnectCountRef.current < maxReconnectAttempts) {
        const delay = Math.min(1000 * Math.pow(2, reconnectCountRef.current), 16000);
        reconnectCountRef.current += 1;
        reconnectTimerRef.current = setTimeout(connect, delay);
      }
    };

    ws.onerror = () => {
      setReadyState(WebSocket.CLOSED);
    };

    ws.onmessage = (event) => {
      const raw = event.data;
      setLastMessage(raw);

      let parsed: any;
      try {
        parsed = JSON.parse(raw);
      } catch {
        parsed = raw;
      }

      setLastJsonMessage(parsed);
      setMessageHistory((prev) => [...prev, parsed]);
      onMessageRef.current?.(parsed);
    };
  }, [url, reconnect, maxReconnectAttempts]);

  useEffect(() => {
    closingRef.current = false;
    connect();

    return () => {
      closingRef.current = true;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((data: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(data);
    }
  }, []);

  const sendJson = useCallback(
    (data: unknown) => {
      send(JSON.stringify(data));
    },
    [send]
  );

  return {
    lastMessage,
    lastJsonMessage,
    messageHistory,
    readyState,
    readyStateLabel: getReadyStateLabel(readyState),
    send,
    sendJson,
  };
}
