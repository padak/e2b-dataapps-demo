export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  toolUse?: {
    tool: string;
    input: any;
  };
}

export interface ToolUse {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  input?: Record<string, unknown>;
  output?: string;
  error?: string;
}

export interface ToolUseEvent {
  type: 'tool_use';
  tool: string;
  input: any;
}

export interface TextDeltaEvent {
  type: 'text_delta';
  delta: string;
}

export interface MessageCompleteEvent {
  type: 'message_complete';
  message: Message;
}

export interface PreviewUpdateEvent {
  type: 'preview_update';
  url: string;
}

export interface ErrorEvent {
  type: 'error';
  error: string;
}

export interface StatusEvent {
  type: 'status';
  status: string;
}

export type WebSocketEvent =
  | ToolUseEvent
  | TextDeltaEvent
  | MessageCompleteEvent
  | PreviewUpdateEvent
  | ErrorEvent
  | StatusEvent;

export interface ChatState {
  messages: Message[];
  isLoading: boolean;
  isConnected: boolean;
  error?: string;
}

// Legacy export for backward compatibility
export type ChatMessage = Message;
