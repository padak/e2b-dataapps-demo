type MessageHandler = (data: any) => void;

// Ping interval to keep connection alive during long operations (30 seconds)
const PING_INTERVAL = 30000;

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private sessionId: string;
  private handlers: Set<MessageHandler> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimeout: number | null = null;
  private pingInterval: number | null = null;
  private isIntentionallyClosed = false;

  constructor(sessionId: string) {
    this.sessionId = sessionId;
  }

  async connect(reconnect: boolean = false): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.isIntentionallyClosed = false;

        // Determine WebSocket URL with reconnect query param
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const reconnectParam = reconnect ? '?reconnect=true' : '';
        const wsUrl = `${protocol}//${host}/ws/chat/${this.sessionId}${reconnectParam}`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          console.log('[WebSocket] Connected to session:', this.sessionId);
          this.reconnectAttempts = 0;
          this.startPingInterval();
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.handlers.forEach((handler) => handler(data));
          } catch (error) {
            console.error('[WebSocket] Failed to parse message:', error);
          }
        };

        this.ws.onerror = (error) => {
          console.error('[WebSocket] Error:', error);
          reject(error);
        };

        this.ws.onclose = (event) => {
          console.log('[WebSocket] Closed:', event.code, event.reason);
          this.ws = null;

          // Attempt reconnection if not intentionally closed
          if (!this.isIntentionallyClosed && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000);
            console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            
            this.reconnectTimeout = window.setTimeout(() => {
              this.connect().catch((error) => {
                console.error('[WebSocket] Reconnection failed:', error);
              });
            }, delay);
          }
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  send(type: string, data?: any): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('[WebSocket] Cannot send message: connection not open');
      return;
    }

    const message = { type, ...data };
    this.ws.send(JSON.stringify(message));
  }

  onMessage(handler: MessageHandler): () => void {
    this.handlers.add(handler);
    
    // Return unsubscribe function
    return () => {
      this.handlers.delete(handler);
    };
  }

  disconnect(): void {
    this.isIntentionallyClosed = true;

    this.stopPingInterval();

    if (this.reconnectTimeout !== null) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.handlers.clear();
    console.log('[WebSocket] Disconnected');
  }

  private startPingInterval(): void {
    this.stopPingInterval();
    this.pingInterval = window.setInterval(() => {
      if (this.isConnected) {
        this.send('ping');
      }
    }, PING_INTERVAL);
  }

  private stopPingInterval(): void {
    if (this.pingInterval !== null) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  get isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}
