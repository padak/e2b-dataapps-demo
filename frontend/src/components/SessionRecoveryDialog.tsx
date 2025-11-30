import { motion, AnimatePresence } from 'framer-motion';
import { Clock, Plus, RotateCcw, X } from 'lucide-react';

interface SessionRecoveryDialogProps {
  isOpen: boolean;
  sessionId: string;
  messageCount: number;
  timestamp: number;
  canReconnect: boolean;
  onRecover: () => void;
  onStartNew: () => void;
  onDismiss: () => void;
}

export default function SessionRecoveryDialog({
  isOpen,
  sessionId,
  messageCount,
  timestamp,
  canReconnect,
  onRecover,
  onStartNew,
  onDismiss,
}: SessionRecoveryDialogProps) {
  if (!isOpen) return null;

  const timeAgo = getTimeAgo(timestamp);

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="relative w-full max-w-md mx-4 p-6 rounded-xl bg-[var(--color-surface)] border border-[var(--color-border)] shadow-xl"
        >
          {/* Close button */}
          <button
            onClick={onDismiss}
            className="absolute top-4 right-4 p-1 rounded-lg text-[var(--color-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-hover)] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>

          {/* Icon */}
          <div className="flex justify-center mb-4">
            <div className="w-12 h-12 rounded-full bg-accent-cyan/10 flex items-center justify-center">
              <Clock className="w-6 h-6 text-accent-cyan" />
            </div>
          </div>

          {/* Title */}
          <h2 className="text-xl font-display font-bold text-center text-[var(--color-bright)] mb-2">
            Previous Session Found
          </h2>

          {/* Description */}
          <p className="text-center text-[var(--color-text)] mb-6">
            You have an unfinished session from {timeAgo} with {messageCount} messages.
            {canReconnect ? (
              <span className="block mt-1 text-sm text-accent-green">
                Server session is still active - you can continue where you left off.
              </span>
            ) : (
              <span className="block mt-1 text-sm text-[var(--color-muted)]">
                Server session expired, but you can restore your chat history.
              </span>
            )}
          </p>

          {/* Session info */}
          <div className="mb-6 p-3 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)]">
            <div className="flex items-center justify-between text-sm">
              <span className="text-[var(--color-muted)]">Session ID</span>
              <span className="font-mono text-[var(--color-text)]">{sessionId}</span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3">
            <button
              onClick={onStartNew}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border border-[var(--color-border)] text-[var(--color-text)] hover:bg-[var(--color-surface-hover)] transition-colors"
            >
              <Plus className="w-4 h-4" />
              Start New
            </button>
            <button
              onClick={onRecover}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-accent-cyan text-white hover:bg-accent-cyan/90 transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
              {canReconnect ? 'Continue' : 'Restore'}
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

function getTimeAgo(timestamp: number): string {
  const seconds = Math.floor((Date.now() - timestamp) / 1000);

  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
  return `${Math.floor(seconds / 86400)} days ago`;
}
