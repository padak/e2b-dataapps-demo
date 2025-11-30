import { useRef, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Terminal, Trash2 } from 'lucide-react';

export interface ConsoleLog {
  id: string;
  timestamp: number;
  message: string;
  type: 'stdout' | 'stderr' | 'info';
}

interface ConsoleOutputProps {
  logs: ConsoleLog[];
  onClear?: () => void;
}

const LOG_COLORS: Record<ConsoleLog['type'], string> = {
  stdout: 'text-[var(--color-text)]',
  stderr: 'text-accent-red',
  info: 'text-accent-cyan',
};

const LOG_ICONS: Record<ConsoleLog['type'], string> = {
  stdout: '›',
  stderr: '✗',
  info: 'ℹ',
};

function formatTimestamp(timestamp: number): string {
  const date = new Date(timestamp);
  const hours = date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');
  const seconds = date.getSeconds().toString().padStart(2, '0');
  const ms = date.getMilliseconds().toString().padStart(3, '0');
  return `${hours}:${minutes}:${seconds}.${ms}`;
}

export default function ConsoleOutput({ logs, onClear }: ConsoleOutputProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // Auto-scroll to bottom when new logs arrive (if autoScroll is enabled)
  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  // Detect manual scroll to disable auto-scroll
  const handleScroll = () => {
    if (containerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
      const isAtBottom = Math.abs(scrollHeight - scrollTop - clientHeight) < 10;
      setAutoScroll(isAtBottom);
    }
  };

  if (logs.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-[var(--color-bg)]/30 text-[var(--color-muted)]">
        <Terminal className="w-12 h-12 mb-3 opacity-20" />
        <p className="text-center text-sm">
          No console output yet.
          <br />
          Logs will appear here when your app runs.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header with controls */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--color-border)] bg-[var(--color-bg)]/50">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-accent-cyan" />
          <span className="text-sm font-mono text-[var(--color-text)]">
            {logs.length} {logs.length === 1 ? 'entry' : 'entries'}
          </span>
        </div>

        {onClear && (
          <button
            onClick={onClear}
            className="flex items-center gap-1.5 px-2 py-1 text-xs rounded transition-colors text-[var(--color-muted)] hover:text-accent-red hover:bg-accent-red/10"
            title="Clear console"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Clear
          </button>
        )}
      </div>

      {/* Log content */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-auto p-4 font-mono text-sm bg-[var(--color-bg)]/30"
      >
        <div className="space-y-1">
          {logs.map((log, index) => (
            <motion.div
              key={log.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.1, delay: Math.min(index * 0.01, 0.05) }}
              className={`flex items-start gap-3 ${LOG_COLORS[log.type]}`}
            >
              <span className="text-[var(--color-muted)] shrink-0 tabular-nums text-xs mt-0.5">
                {formatTimestamp(log.timestamp)}
              </span>
              <span className="shrink-0 w-4 text-center mt-0.5">{LOG_ICONS[log.type]}</span>
              <span className="break-all whitespace-pre-wrap flex-1">{log.message}</span>
            </motion.div>
          ))}

          {/* Auto-scroll indicator */}
          {!autoScroll && (
            <div className="sticky bottom-0 left-0 right-0 flex justify-center py-2">
              <button
                onClick={() => {
                  setAutoScroll(true);
                  if (containerRef.current) {
                    containerRef.current.scrollTop = containerRef.current.scrollHeight;
                  }
                }}
                className="px-3 py-1 text-xs rounded-full bg-accent-cyan text-white hover:bg-accent-cyan/90 transition-colors"
              >
                Scroll to bottom
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
