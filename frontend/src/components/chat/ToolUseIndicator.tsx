import { motion } from 'framer-motion';
import { Wrench, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { ToolUse } from '../../types/chat';

interface ToolUseIndicatorProps {
  tool: ToolUse;
}

const TOOL_COLORS: Record<ToolUse['status'], string> = {
  pending: 'bg-[var(--color-muted)]/20 text-[var(--color-muted)]',
  running: 'bg-accent-cyan/20 text-accent-cyan',
  completed: 'bg-accent-green/20 text-accent-green',
  error: 'bg-accent-red/20 text-accent-red',
};

const TOOL_ICONS: Record<ToolUse['status'], React.ReactNode> = {
  pending: <Wrench className="w-3 h-3" />,
  running: <Loader2 className="w-3 h-3 animate-spin" />,
  completed: <CheckCircle2 className="w-3 h-3" />,
  error: <XCircle className="w-3 h-3" />,
};

export default function ToolUseIndicator({ tool }: ToolUseIndicatorProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium ${TOOL_COLORS[tool.status]}`}
    >
      {TOOL_ICONS[tool.status]}
      <span>{tool.name}</span>
      {tool.status === 'running' && (
        <motion.span
          className="inline-block w-1.5 h-1.5 rounded-full bg-current"
          animate={{
            opacity: [1, 0.5, 1],
            scale: [1, 1.2, 1],
          }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      )}
    </motion.div>
  );
}
