import { useState, useEffect } from 'react';
import { FolderOpen, FileCode, RefreshCw, ChevronRight } from 'lucide-react';
import { ScriptFile } from '../types';

interface ScriptFilesSelectorProps {
  onSelect: (code: string) => void;
}

export default function ScriptFilesSelector({ onSelect }: ScriptFilesSelectorProps) {
  const [scripts, setScripts] = useState<ScriptFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const fetchScripts = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/scripts');
      if (response.ok) {
        const data = await response.json();
        setScripts(data.scripts || []);
      }
    } catch (error) {
      console.error('Failed to fetch scripts:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScripts();
  }, []);

  const handleSelect = async (script: ScriptFile) => {
    try {
      const response = await fetch(`/api/scripts/${encodeURIComponent(script.name)}`);
      if (response.ok) {
        const data = await response.json();
        onSelect(data.content);
      }
    } catch (error) {
      console.error('Failed to load script:', error);
    }
  };

  return (
    <div className="space-y-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-sm font-medium text-[var(--color-text)] w-full hover:text-accent-cyan transition-colors"
      >
        <ChevronRight className={`w-4 h-4 transition-transform ${expanded ? 'rotate-90' : ''}`} />
        <FolderOpen className="w-4 h-4 text-accent-orange" />
        <span>Scripts from /scripts</span>
        <span className="ml-auto text-xs text-[var(--color-muted)]">
          {scripts.length} files
        </span>
        <button
          onClick={(e) => {
            e.stopPropagation();
            fetchScripts();
          }}
          className="p-1 hover:bg-[var(--color-border)] rounded transition-colors"
          title="Refresh"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </button>

      {expanded && (
        <div className="ml-6 space-y-1 max-h-48 overflow-y-auto">
          {scripts.length === 0 ? (
            <p className="text-xs text-[var(--color-muted)] py-2">
              No scripts found in /scripts folder
            </p>
          ) : (
            scripts.map((script) => (
              <button
                key={script.name}
                onClick={() => handleSelect(script)}
                className="flex items-center gap-2 w-full p-2 rounded-lg text-left
                  bg-[var(--color-bg)] border border-[var(--color-border)]
                  hover:border-accent-cyan/50 hover:bg-accent-cyan/5
                  transition-colors text-sm group"
              >
                <FileCode className="w-4 h-4 text-[var(--color-muted)] group-hover:text-accent-cyan shrink-0" />
                <span className="truncate text-[var(--color-text)]">{script.name}</span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
