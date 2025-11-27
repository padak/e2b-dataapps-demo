import { useRef, useEffect } from 'react';
import { Message } from '../../types/chat';
import ChatMessage from './ChatMessage';

interface MessageListProps {
  messages: Message[];
}

export default function MessageList({ messages }: MessageListProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto overflow-x-hidden px-4 py-6"
    >
      {messages.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-full text-[var(--color-muted)]">
          <div className="text-6xl mb-4 opacity-20">💬</div>
          <p className="text-center text-sm">
            No messages yet.
            <br />
            <span className="text-accent-cyan">Start a conversation</span> to build your app.
          </p>
        </div>
      ) : (
        <div className="space-y-6 max-w-4xl mx-auto">
          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}
