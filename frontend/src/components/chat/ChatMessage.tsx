import { motion } from 'framer-motion';
import { User, Bot } from 'lucide-react';
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

function renderContent(content: string): React.ReactNode {
  // Simple markdown-like rendering for code blocks
  const parts = content.split(/(```[\s\S]*?```)/g);

  return parts.map((part, index) => {
    if (part.startsWith('```')) {
      const code = part.slice(3, -3).trim();
      const [lang, ...codeLines] = code.split('\n');
      const codeContent = codeLines.join('\n');

      return (
        <pre
          key={index}
          className="mt-2 mb-2 p-3 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] overflow-x-auto"
        >
          {lang && (
            <div className="text-xs text-[var(--color-muted)] mb-2 font-sans">{lang}</div>
          )}
          <code className="text-sm font-mono text-[var(--color-text)]">{codeContent}</code>
        </pre>
      );
    }

    // Render inline code
    return part.split(/(`[^`]+`)/g).map((subPart, subIndex) => {
      if (subPart.startsWith('`') && subPart.endsWith('`')) {
        return (
          <code
            key={`${index}-${subIndex}`}
            className="px-1.5 py-0.5 rounded bg-[var(--color-bg)] text-accent-cyan text-sm font-mono"
          >
            {subPart.slice(1, -1)}
          </code>
        );
      }
      return <span key={`${index}-${subIndex}`}>{subPart}</span>;
    });
  });
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

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
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4 text-accent-green" />}
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
          <div className="text-sm whitespace-pre-wrap break-words">
            {renderContent(message.content)}
          </div>

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
