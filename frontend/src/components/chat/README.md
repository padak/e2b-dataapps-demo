# Chat Components

A collection of React components for building a chat interface in the App Builder frontend.

## Components

### ChatPanel
Main chat panel container that includes the header, message list, and input area.

```tsx
import { ChatPanel } from './components/chat';
import { ChatState } from './types/chat';

function App() {
  const [chatState, setChatState] = useState<ChatState>({
    messages: [],
    isLoading: false,
    isConnected: true,
  });

  const handleSendMessage = (message: string) => {
    // Handle sending message
  };

  return (
    <ChatPanel
      chatState={chatState}
      onSendMessage={handleSendMessage}
      title="App Builder Chat"
    />
  );
}
```

**Props:**
- `chatState: ChatState` - Current chat state including messages, loading, and connection status
- `onSendMessage: (message: string) => void` - Callback when user sends a message
- `title?: string` - Optional panel title (default: "App Builder Chat")

### MessageList
Scrollable message list that auto-scrolls to the bottom on new messages.

```tsx
import { MessageList } from './components/chat';

<MessageList messages={messages} />
```

**Props:**
- `messages: Message[]` - Array of chat messages

**Features:**
- Auto-scroll to bottom on new messages
- Empty state with helpful message
- Different styling for user vs assistant messages
- Shows tool use indicators

### ChatInput
Input area with auto-growing textarea and send button.

```tsx
import { ChatInput } from './components/chat';

<ChatInput
  onSend={handleSend}
  isLoading={false}
  disabled={false}
/>
```

**Props:**
- `onSend: (message: string) => void` - Callback when message is sent
- `isLoading: boolean` - Shows loading spinner in send button
- `disabled?: boolean` - Disables input and send button

**Features:**
- Auto-growing textarea (max 6 lines)
- Enter to send, Shift+Enter for newline
- Character count display
- Loading spinner when waiting for response
- Keyboard shortcuts hint

### ChatMessage
Individual message component with role-based styling.

```tsx
import { ChatMessage } from './components/chat';

<ChatMessage message={message} />
```

**Props:**
- `message: Message` - Message object

**Features:**
- User messages: right-aligned, cyan accent
- Assistant messages: left-aligned, surface color
- Avatar icons (User/Bot)
- Timestamp display
- Markdown-like content rendering (code blocks, inline code)
- Tool use indicator badge

### ToolUseIndicator
Shows when AI is using a tool with status-based styling.

```tsx
import { ToolUseIndicator } from './components/chat';

<ToolUseIndicator tool={toolUse} />
```

**Props:**
- `tool: ToolUse` - Tool use object with status

**Features:**
- Status-based colors (pending, running, completed, error)
- Animated pulse for running status
- Different icons for each status

## Types

### Message
```typescript
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  toolUse?: {
    tool: string;
    input: any;
  };
}
```

### ChatState
```typescript
interface ChatState {
  messages: Message[];
  isLoading: boolean;
  isConnected: boolean;
  error?: string;
}
```

### ToolUse
```typescript
interface ToolUse {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  input?: Record<string, unknown>;
  output?: string;
  error?: string;
}
```

## Styling Patterns

All components follow the established styling patterns:

- **CSS Variables**: Use `var(--color-*)` for theming
  - `--color-bg`: Background color
  - `--color-surface`: Surface/card color
  - `--color-border`: Border color
  - `--color-text`: Primary text color
  - `--color-muted`: Muted text color
  - `--color-bright`: Bright text color

- **Accent Colors**: Direct Tailwind classes
  - `accent-cyan`: Primary accent (buttons, highlights)
  - `accent-green`: Success states
  - `accent-red`: Error states
  - `accent-orange`: Warning states

- **Animations**: Framer Motion for smooth transitions
  - Message fade-in and slide up
  - Tool use indicator pulse
  - Auto-scroll smooth behavior

- **Icons**: Lucide React icons
  - `MessageSquare`, `User`, `Bot` for chat
  - `Send`, `Loader2` for input
  - `Wifi`, `WifiOff` for connection status
  - `Wrench`, `CheckCircle2`, `XCircle` for tools

## Example Usage

```tsx
import { useState, useEffect } from 'react';
import { ChatPanel } from './components/chat';
import { ChatState, Message } from './types/chat';

function AppBuilderChat() {
  const [chatState, setChatState] = useState<ChatState>({
    messages: [],
    isLoading: false,
    isConnected: false,
  });

  // Connect to WebSocket
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws');

    ws.onopen = () => {
      setChatState(prev => ({ ...prev, isConnected: true }));
    };

    ws.onclose = () => {
      setChatState(prev => ({ ...prev, isConnected: false }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      // Handle different message types
    };

    return () => ws.close();
  }, []);

  const handleSendMessage = (content: string) => {
    const newMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: Date.now(),
    };

    setChatState(prev => ({
      ...prev,
      messages: [...prev.messages, newMessage],
      isLoading: true,
    }));

    // Send to WebSocket
    // ws.send(JSON.stringify({ message: content }));
  };

  return (
    <div className="h-screen">
      <ChatPanel
        chatState={chatState}
        onSendMessage={handleSendMessage}
        title="App Builder"
      />
    </div>
  );
}
```
