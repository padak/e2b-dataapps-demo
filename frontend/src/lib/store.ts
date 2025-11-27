import { create } from 'zustand';
import { Message } from '../types/chat';

interface AppState {
  sessionId: string | null;
  messages: Message[];
  previewUrl: string | null;
  isConnected: boolean;
  isLoading: boolean;

  setSessionId: (id: string) => void;
  addMessage: (message: Message) => void;
  appendToLastMessage: (content: string) => void;
  setPreviewUrl: (url: string | null) => void;
  setConnected: (connected: boolean) => void;
  setLoading: (loading: boolean) => void;
  reset: () => void;
}

const initialState = {
  sessionId: null,
  messages: [],
  previewUrl: null,
  isConnected: false,
  isLoading: false,
};

export const useAppStore = create<AppState>((set) => ({
  ...initialState,

  setSessionId: (id: string) =>
    set({ sessionId: id }),

  addMessage: (message: Message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  appendToLastMessage: (content: string) =>
    set((state) => {
      if (state.messages.length === 0) {
        // No messages yet, create a new assistant message
        const newMessage: Message = {
          id: `msg-${Date.now()}`,
          role: 'assistant',
          content,
          timestamp: Date.now(),
        };
        return { messages: [newMessage] };
      }

      // Append to the last message
      const messages = [...state.messages];
      const lastIndex = messages.length - 1;
      messages[lastIndex] = {
        ...messages[lastIndex],
        content: messages[lastIndex].content + content,
      };

      return { messages };
    }),

  setPreviewUrl: (url: string | null) =>
    set({ previewUrl: url }),

  setConnected: (connected: boolean) =>
    set({ isConnected: connected }),

  setLoading: (loading: boolean) =>
    set({ isLoading: loading }),

  reset: () =>
    set(initialState),
}));
