# App Builder Library

This directory contains the core utilities for the App Builder functionality.

## Files

### websocket.ts
WebSocket client for real-time communication with the backend.

**Usage:**
```typescript
import { WebSocketClient } from './lib';

const client = new WebSocketClient('session-id-123');

// Connect to WebSocket
await client.connect();

// Listen for messages
const unsubscribe = client.onMessage((data) => {
  console.log('Received:', data);
});

// Send a message
client.send('user_message', { content: 'Hello!' });

// Disconnect when done
client.disconnect();

// Or unsubscribe from messages
unsubscribe();
```

**Features:**
- Automatic reconnection with exponential backoff
- Type-safe message handling
- Multiple message handlers support
- Clean disconnection management

### store.ts
Zustand state management store for the App Builder.

**Usage:**
```typescript
import { useAppStore } from './lib';

function MyComponent() {
  const { 
    messages, 
    addMessage, 
    appendToLastMessage,
    previewUrl,
    setPreviewUrl,
    isConnected,
    setConnected,
    isLoading,
    setLoading 
  } = useAppStore();

  // Add a new message
  const handleNewMessage = () => {
    addMessage({
      id: 'msg-123',
      role: 'user',
      content: 'Hello!',
      timestamp: Date.now(),
    });
  };

  // Append to streaming message
  const handleStreamChunk = (chunk: string) => {
    appendToLastMessage(chunk);
  };

  // Update preview URL
  const handlePreviewReady = (url: string) => {
    setPreviewUrl(url);
  };

  return (
    <div>
      {messages.map(msg => (
        <div key={msg.id}>{msg.content}</div>
      ))}
    </div>
  );
}
```

**State:**
- `sessionId`: Current session ID
- `messages`: Array of chat messages
- `previewUrl`: URL of the preview iframe
- `isConnected`: WebSocket connection status
- `isLoading`: Loading state for async operations

**Actions:**
- `setSessionId(id)`: Set the current session ID
- `addMessage(message)`: Add a new message to the chat
- `appendToLastMessage(content)`: Append text to the last message (for streaming)
- `setPreviewUrl(url)`: Update the preview URL
- `setConnected(connected)`: Update connection status
- `setLoading(loading)`: Update loading state
- `reset()`: Reset the store to initial state

### index.ts
Barrel export for all lib modules.

```typescript
import { WebSocketClient, useAppStore } from './lib';
```

## Types

See `/src/types/chat.ts` for all TypeScript type definitions including:
- `Message`: Chat message structure
- `WebSocketEvent`: Union type for all WebSocket events
- `ToolUseEvent`, `TextDeltaEvent`, `MessageCompleteEvent`, etc.
