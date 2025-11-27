import { useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { LogEntry } from '../types';

interface LogTerminalProps {
  logs: LogEntry[];
}

const LOG_ICONS: Record<LogEntry['level'], string> = {
  info: '→',
  success: '✓',
  error: '✗',
  stream: '│',
  debug: '·',
};

const LOG_COLORS: Record<LogEntry['level'], string> = {
  info: 'text-[var(--color-text)]',
  success: 'text-accent-green',
  error: 'text-accent-red',
  stream: 'text-[var(--color-muted)]',
  debug: 'text-[var(--color-muted)] opacity-70',
};

function formatTimestamp(timestamp: number, startTime?: number): string {
  if (startTime) {
    const elapsed = (timestamp - startTime) / 1000;
    return `[${elapsed.toFixed(2).padStart(6, ' ')}s]`;
  }
  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-US', { hour12: false });
}

export default function LogTerminal({ logs }: LogTerminalProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const startTime = logs.length > 0 ? logs[0].timestamp : undefined;

  // Auto-scroll to bottom
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div
      ref={containerRef}
      className="h-full overflow-auto p-4 font-mono text-sm bg-[var(--color-bg)]/30"
    >
      {logs.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-full text-[var(--color-muted)]">
          <div className="text-4xl mb-4 opacity-20">⌘</div>
          <p className="text-center">
            No logs yet.
            <br />
            <span className="text-accent-cyan">Launch</span> a sandbox to see output here.
          </p>
        </div>
      ) : (
        <div className="space-y-0.5">
          {logs.map((log, index) => (
            <motion.div
              key={log.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.15, delay: Math.min(index * 0.02, 0.1) }}
              className={`log-line flex items-start gap-2 ${LOG_COLORS[log.level]}`}
            >
              <span className="text-[var(--color-muted)] shrink-0 tabular-nums">
                {formatTimestamp(log.timestamp, startTime)}
              </span>
              <span className="shrink-0 w-4 text-center">{LOG_ICONS[log.level]}</span>
              <span className="break-all whitespace-pre-wrap">{log.message}</span>
            </motion.div>
          ))}
          {/* Blinking cursor at the end */}
          <div className="flex items-center gap-2 text-[var(--color-muted)] mt-1">
            <span className="invisible">{'[  0.00s]'}</span>
            <span className="terminal-cursor" />
          </div>
        </div>
      )}
    </div>
  );
}
