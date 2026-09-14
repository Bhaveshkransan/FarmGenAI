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
    if (typeof window !== 'undefined') {
      const isHttps = window.location.protocol === 'https:';
      const defaultWsProto = isHttps ? 'wss:' : 'ws:';
      if (finalUrl.startsWith('/')) {
        finalUrl = `${defaultWsProto}//${window.location.host}${finalUrl}`;
      } else if (finalUrl.includes('localhost:8000') && window.location.hostname !== 'localhost') {
        finalUrl = `${defaultWsProto}//${window.location.host}/api/v1/ws`;
      }
    }
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

      ws.current.onclose = () => {
        setIsConnected(false);
        if (pingInterval.current) clearInterval(pingInterval.current);
        
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
