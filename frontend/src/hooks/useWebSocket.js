import { useEffect, useRef, useState, useCallback } from 'react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

/**
 * WebSocket hook for real-time job updates and log streaming.
 * Auto-reconnects on disconnect with exponential backoff.
 */
export function useWebSocket(onMessage) {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimeout = useRef(null);
  const reconnectDelay = useRef(1000);
  const onMessageRef = useRef(onMessage);

  // Keep callback ref current without triggering reconnect
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    // Convert http(s) to ws(s)
    const wsUrl = BACKEND_URL.replace(/^http/, 'ws') + '/api/ws';

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        reconnectDelay.current = 1000;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessageRef.current?.(data);
        } catch (e) {
          // Non-JSON message, ignore
        }
      };

      ws.onclose = () => {
        setConnected(false);
        wsRef.current = null;
        // Reconnect with exponential backoff (max 10s)
        reconnectTimeout.current = setTimeout(() => {
          reconnectDelay.current = Math.min(reconnectDelay.current * 1.5, 10000);
          connect();
        }, reconnectDelay.current);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch (e) {
      // Connection failed, retry
      reconnectTimeout.current = setTimeout(connect, reconnectDelay.current);
    }
  }, []);

  useEffect(() => {
    connect();
    // Ping to keep alive
    const pingInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send('ping');
      }
    }, 30000);

    return () => {
      clearInterval(pingInterval);
      clearTimeout(reconnectTimeout.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { connected };
}
