import { useCallback } from 'react';
import { Message } from '../types/chat';
import { CodeFile } from '../components/preview/CodeView';

const STORAGE_KEY = 'e2b-app-builder-session';
const SESSION_TTL = 30 * 60 * 1000; // 30 minutes

interface StoredSession {
  sessionId: string;
  messages: Message[];
  codeFiles: CodeFile[];
  previewUrl: string | null;
  sandboxId: string | null;
  timestamp: number;
}

export function useSessionStorage() {
  const saveSession = useCallback((data: Omit<StoredSession, 'timestamp'>) => {
    const session: StoredSession = {
      ...data,
      timestamp: Date.now(),
    };
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    } catch (error) {
      console.error('Failed to save session to localStorage:', error);
    }
  }, []);

  const loadSession = useCallback((): StoredSession | null => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (!stored) return null;

      const session: StoredSession = JSON.parse(stored);

      // Check if session is expired
      if (Date.now() - session.timestamp > SESSION_TTL) {
        localStorage.removeItem(STORAGE_KEY);
        return null;
      }

      return session;
    } catch (error) {
      console.error('Failed to load session from localStorage:', error);
      return null;
    }
  }, []);

  const clearSession = useCallback(() => {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (error) {
      console.error('Failed to clear session from localStorage:', error);
    }
  }, []);

  const hasStoredSession = useCallback((): boolean => {
    const session = loadSession();
    return session !== null && session.messages.length > 0;
  }, [loadSession]);

  return {
    saveSession,
    loadSession,
    clearSession,
    hasStoredSession,
  };
}
