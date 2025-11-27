import { Sun, Moon, Monitor } from 'lucide-react';
import { Theme } from '../hooks/useTheme';

interface ThemeToggleProps {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

export default function ThemeToggle({ theme, setTheme }: ThemeToggleProps) {
  return (
    <div className="flex items-center gap-1 p-1 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)]">
      <button
        onClick={() => setTheme('light')}
        className={`p-1.5 rounded transition-colors ${
          theme === 'light'
            ? 'bg-accent-cyan/20 text-accent-cyan'
            : 'text-[var(--color-muted)] hover:text-[var(--color-text)]'
        }`}
        title="Light mode"
      >
        <Sun className="w-4 h-4" />
      </button>
      <button
        onClick={() => setTheme('dark')}
        className={`p-1.5 rounded transition-colors ${
          theme === 'dark'
            ? 'bg-accent-cyan/20 text-accent-cyan'
            : 'text-[var(--color-muted)] hover:text-[var(--color-text)]'
        }`}
        title="Dark mode"
      >
        <Moon className="w-4 h-4" />
      </button>
    </div>
  );
}
