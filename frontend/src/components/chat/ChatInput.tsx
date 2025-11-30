import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { Send, Loader2 } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  isLoading: boolean;
  disabled?: boolean;
}

export default function ChatInput({ onSend, isLoading, disabled }: ChatInputProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const scrollHeight = textareaRef.current.scrollHeight;
      // Max 6 lines (approximately 24px per line)
      const maxHeight = 24 * 6;
      textareaRef.current.style.height = `${Math.min(scrollHeight, maxHeight)}px`;
    }
  }, [message]);

  const handleSend = () => {
    if (message.trim() && !isLoading && !disabled) {
      onSend(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter to send, Shift+Enter for newline
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isDisabled = isLoading || disabled || !message.trim();

  return (
    <div className="border-t border-[var(--color-border)] bg-[var(--color-surface)] p-4">
      <div className="max-w-4xl mx-auto flex gap-3 items-end">
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message... (Enter to send, Shift+Enter for newline)"
            disabled={disabled}
            rows={1}
            className="w-full resize-none rounded-lg px-4 py-3 pr-12 bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text)] placeholder:text-[var(--color-muted)] focus:outline-none focus:border-accent-cyan focus:ring-2 focus:ring-accent-cyan/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            style={{ maxHeight: '144px', overflow: 'auto' }}
          />
          <div className="absolute bottom-3 right-3 text-xs text-[var(--color-muted)]">
            {message.length > 0 && <span>{message.length}</span>}
          </div>
        </div>

        <button
          onClick={handleSend}
          disabled={isDisabled}
          className={`flex-shrink-0 w-11 h-11 rounded-lg flex items-center justify-center transition-all ${
            isDisabled
              ? 'bg-[var(--color-border)] text-[var(--color-muted)] cursor-not-allowed'
              : 'bg-accent-cyan text-white hover:bg-accent-cyan/90 hover:shadow-lg hover:shadow-accent-cyan/20 active:scale-95'
          }`}
          title={isDisabled ? 'Type a message to send' : 'Send message (Enter)'}
        >
          {isLoading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
        </button>
      </div>

      {/* Keyboard hint */}
      <div className="max-w-4xl mx-auto mt-2 text-xs text-[var(--color-muted)] text-center">
        Press <kbd className="px-1.5 py-0.5 rounded bg-[var(--color-bg)] border border-[var(--color-border)]">Enter</kbd> to send,{' '}
        <kbd className="px-1.5 py-0.5 rounded bg-[var(--color-bg)] border border-[var(--color-border)]">Shift+Enter</kbd> for new line
      </div>
    </div>
  );
}
