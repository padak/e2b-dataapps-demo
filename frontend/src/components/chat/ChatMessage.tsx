import { motion } from 'framer-motion';
import { User, Bot, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Message } from '../../types/chat';

interface ChatMessageProps {
  message: Message;
}

function formatTimestamp(timestamp: number): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });
}

// Typing indicator component
function TypingIndicator() {
  return (
    <div className="flex items-center gap-2 text-[var(--color-muted)]">
      <Loader2 className="w-4 h-4 animate-spin text-accent-cyan" />
      <span className="text-sm">Thinking...</span>
    </div>
  );
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const isEmpty = !message.content || message.content.trim() === '';
  const showTypingIndicator = !isUser && isEmpty;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
    >
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${
          isUser
            ? 'bg-accent-cyan/20 text-accent-cyan'
            : 'bg-[var(--color-surface)] border border-[var(--color-border)]'
        }`}
      >
        {isUser ? (
          <User className="w-4 h-4" />
        ) : (
          <Bot className={`w-4 h-4 ${showTypingIndicator ? 'text-accent-cyan animate-pulse' : 'text-accent-green'}`} />
        )}
      </div>

      {/* Message Content */}
      <div className={`flex-1 max-w-[80%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        <div
          className={`rounded-lg px-4 py-2.5 ${
            isUser
              ? 'bg-accent-cyan/20 text-[var(--color-text)]'
              : 'bg-[var(--color-surface)] border border-[var(--color-border)]'
          }`}
        >
          {showTypingIndicator ? (
            <TypingIndicator />
          ) : (
          <div className="text-sm prose prose-sm dark:prose-invert max-w-none prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5">
            <ReactMarkdown
              components={{
                // Custom code block rendering
                code({ className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '');
                  const isInline = !match && !className;

                  if (isInline) {
                    return (
                      <code
                        className="px-1.5 py-0.5 rounded bg-[var(--color-bg)] text-accent-cyan text-sm font-mono"
                        {...props}
                      >
                        {children}
                      </code>
                    );
                  }

                  return (
                    <pre className="mt-2 mb-2 p-3 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] overflow-x-auto">
                      {match && (
                        <div className="text-xs text-[var(--color-muted)] mb-2 font-sans">{match[1]}</div>
                      )}
                      <code className="text-sm font-mono text-[var(--color-text)]" {...props}>
                        {children}
                      </code>
                    </pre>
                  );
                },
                // Style other elements
                p({ children }) {
                  return <p className="text-[var(--color-text)] leading-relaxed">{children}</p>;
                },
                h1({ children }) {
                  return <h1 className="text-lg font-bold text-[var(--color-bright)]">{children}</h1>;
                },
                h2({ children }) {
                  return <h2 className="text-base font-bold text-[var(--color-bright)]">{children}</h2>;
                },
                h3({ children }) {
                  return <h3 className="text-sm font-bold text-[var(--color-bright)]">{children}</h3>;
                },
                ul({ children }) {
                  return <ul className="list-disc list-inside text-[var(--color-text)]">{children}</ul>;
                },
                ol({ children }) {
                  return <ol className="list-decimal list-inside text-[var(--color-text)]">{children}</ol>;
                },
                li({ children }) {
                  return <li className="text-[var(--color-text)]">{children}</li>;
                },
                strong({ children }) {
                  return <strong className="font-semibold text-[var(--color-bright)]">{children}</strong>;
                },
                em({ children }) {
                  return <em className="italic">{children}</em>;
                },
                a({ href, children }) {
                  return (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-accent-cyan hover:underline"
                    >
                      {children}
                    </a>
                  );
                },
                blockquote({ children }) {
                  return (
                    <blockquote className="border-l-2 border-accent-cyan pl-3 italic text-[var(--color-muted)]">
                      {children}
                    </blockquote>
                  );
                },
                hr() {
                  return (
                    <hr className="my-4 border-t border-[var(--color-border)] opacity-50" />
                  );
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
          )}

          {/* Tool Use Indicator */}
          {message.toolUse && (
            <div className="mt-2">
              <div className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium bg-accent-cyan/20 text-accent-cyan">
                <span>Used: {message.toolUse.tool}</span>
              </div>
            </div>
          )}
        </div>

        {/* Timestamp */}
        <div className="mt-1 px-1 text-xs text-[var(--color-muted)]">
          {formatTimestamp(message.timestamp)}
        </div>
      </div>
    </motion.div>
  );
}
