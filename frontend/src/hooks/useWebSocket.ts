import { useState, useEffect, useRef, useCallback } from 'react';

export function useWebSocket(url) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const ws = useRef(null);
  const reconnectTimeout = useRef(null);
  const pingInterval = useRef(null);
  const reconnectAttempts = useRef(0);
  const MAX_RECONNECT_ATTEMPTS = 5;

  const connect = useCallback(() => {
    if (!url) return;

    let finalUrl = url;
    const token = localStorage.getItem('agri_token');
    if (token && !finalUrl.includes('token=')) {
      finalUrl = finalUrl.includes('?') ? `${finalUrl}&token=${token}` : `${finalUrl}?token=${token}`;
    }

    try {
      ws.current = new WebSocket(finalUrl);

      ws.current.onopen = () => {
        setIsConnected(true);
        reconnectAttempts.current = 0;
        
        // Start Heartbeat
        pingInterval.current = setInterval(() => {
          if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({ type: 'ping' }));
          }
        }, 30000); // 30 seconds
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          // Ignore pong responses
          if (data.type === 'pong') return;
          setLastMessage(data);
        } catch (err) {
          setLastMessage(event.data);
        }
      };

      ws.current.onclose = (event) => {
        setIsConnected(false);
        if (pingInterval.current) clearInterval(pingInterval.current);
        
        // Don't retry on Policy Violation (1008) or unauthorized (401/403 mappings if any)
        if (event.code === 1008 || event.code === 1011) {
          console.error(`WebSocket closed with code ${event.code}. Halting reconnect loop.`);
          return;
        }

        // Exponential backoff reconnect
        if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          const timeout = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000);
          reconnectTimeout.current = setTimeout(connect, timeout);
          reconnectAttempts.current += 1;
        }
      };
    } catch (err) {
      console.error('WebSocket connection error:', err);
    }
  }, [url]);

  useEffect(() => {
    connect();
    
    return () => {
      if (ws.current) {
        ws.current.close();
      }
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      if (pingInterval.current) {
        clearInterval(pingInterval.current);
      }
    };
  }, [connect]);

  const sendMessage = useCallback((msg) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(msg));
    }
  }, []);

  return { isConnected, lastMessage, sendMessage };
}
