import { FileCode, Sparkles, Hand, BarChart3, FileText, LucideIcon } from 'lucide-react';
import { EXAMPLE_SCRIPTS } from '../types';

interface ExampleSelectorProps {
  onSelect: (code: string) => void;
}

const EXAMPLE_INFO: Record<string, { icon: LucideIcon; description: string; color: string }> = {
  'Hello World': {
    icon: Hand,
    description: 'Simple greeting app with balloons',
    color: 'text-accent-orange',
  },
  'Data Dashboard': {
    icon: BarChart3,
    description: 'Interactive charts with Plotly',
    color: 'text-accent-cyan',
  },
  'Interactive Form': {
    icon: FileText,
    description: 'Contact form with validation',
    color: 'text-accent-purple',
  },
};

export default function ExampleSelector({ onSelect }: ExampleSelectorProps) {
  const examples = Object.keys(EXAMPLE_SCRIPTS);

  return (
    <div className="space-y-2">
      <label className="flex items-center gap-2 text-sm font-medium text-[var(--color-text)]">
        <Sparkles className="w-4 h-4 text-accent-purple" />
        Load Example
      </label>

      <div className="grid grid-cols-1 gap-2">
        {examples.map((name) => {
          const info = EXAMPLE_INFO[name];
          const Icon = info.icon;
          return (
            <button
              key={name}
              onClick={() => onSelect(EXAMPLE_SCRIPTS[name])}
              className="flex items-center gap-3 p-3 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] hover:border-accent-purple/50 hover:bg-accent-purple/5 transition-colors text-left group"
            >
              <Icon className={`w-5 h-5 ${info.color}`} />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-[var(--color-text)] group-hover:text-accent-purple transition-colors">
                  {name}
                </p>
                <p className="text-xs text-[var(--color-muted)] truncate">{info.description}</p>
              </div>
              <FileCode className="w-4 h-4 text-[var(--color-muted)] group-hover:text-accent-purple transition-colors shrink-0" />
            </button>
          );
        })}
      </div>
    </div>
  );
}
