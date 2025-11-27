import { useState, useRef } from 'react';
import { ChevronRight, Plus, Trash2, Variable, Eye, EyeOff, Upload } from 'lucide-react';

interface EnvVarsEditorProps {
  envVars: Record<string, string>;
  onChange: (envVars: Record<string, string>) => void;
}

export default function EnvVarsEditor({ envVars, onChange }: EnvVarsEditorProps) {
  const [expanded, setExpanded] = useState(false);
  const [newKey, setNewKey] = useState('');
  const [newValue, setNewValue] = useState('');
  const [showValues, setShowValues] = useState<Record<string, boolean>>({});
  const fileInputRef = useRef<HTMLInputElement>(null);

  const entries = Object.entries(envVars);

  const parseEnvFile = (content: string): Record<string, string> => {
    const result: Record<string, string> = {};
    const lines = content.split('\n');

    for (const line of lines) {
      const trimmed = line.trim();
      // Skip empty lines and comments
      if (!trimmed || trimmed.startsWith('#')) continue;

      const match = trimmed.match(/^([^=]+)=(.*)$/);
      if (match) {
        const key = match[1].trim();
        let value = match[2].trim();
        // Remove surrounding quotes if present
        if ((value.startsWith('"') && value.endsWith('"')) ||
            (value.startsWith("'") && value.endsWith("'"))) {
          value = value.slice(1, -1);
        }
        result[key] = value;
      }
    }
    return result;
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      const parsed = parseEnvFile(content);
      onChange({ ...envVars, ...parsed });
    };
    reader.readAsText(file);

    // Reset input so same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleAdd = () => {
    if (newKey.trim() && newValue.trim()) {
      onChange({ ...envVars, [newKey.trim()]: newValue.trim() });
      setNewKey('');
      setNewValue('');
    }
  };

  const handleRemove = (key: string) => {
    const updated = { ...envVars };
    delete updated[key];
    onChange(updated);
  };

  const handleUpdate = (oldKey: string, newKeyName: string, value: string) => {
    const updated = { ...envVars };
    if (oldKey !== newKeyName) {
      delete updated[oldKey];
    }
    updated[newKeyName] = value;
    onChange(updated);
  };

  const toggleShowValue = (key: string) => {
    setShowValues((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="space-y-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-sm font-medium text-[var(--color-text)] w-full hover:text-accent-cyan transition-colors"
      >
        <ChevronRight className={`w-4 h-4 transition-transform ${expanded ? 'rotate-90' : ''}`} />
        <Variable className="w-4 h-4 text-accent-purple" />
        <span>Environment Variables</span>
        <span className="ml-auto text-xs text-[var(--color-muted)]">
          {entries.length} vars
        </span>
      </button>

      {expanded && (
        <div className="ml-6 space-y-2">
          {/* Existing variables */}
          {entries.map(([key, value]) => (
            <div key={key} className="flex items-center gap-2">
              <input
                type="text"
                value={key}
                onChange={(e) => handleUpdate(key, e.target.value, value)}
                className="flex-1 input font-mono text-xs"
                placeholder="KEY"
              />
              <span className="text-[var(--color-muted)]">=</span>
              <div className="flex-1 relative">
                <input
                  type={showValues[key] ? 'text' : 'password'}
                  value={value}
                  onChange={(e) => handleUpdate(key, key, e.target.value)}
                  className="w-full input font-mono text-xs pr-8"
                  placeholder="value"
                />
                <button
                  onClick={() => toggleShowValue(key)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-[var(--color-muted)] hover:text-[var(--color-text)]"
                >
                  {showValues[key] ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                </button>
              </div>
              <button
                onClick={() => handleRemove(key)}
                className="p-1.5 text-[var(--color-muted)] hover:text-accent-red transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}

          {/* Add new variable */}
          <div className="flex items-center gap-2 pt-2 border-t border-[var(--color-border)]">
            <input
              type="text"
              value={newKey}
              onChange={(e) => setNewKey(e.target.value.toUpperCase())}
              className="flex-1 input font-mono text-xs"
              placeholder="NEW_KEY"
              onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
            />
            <span className="text-[var(--color-muted)]">=</span>
            <input
              type="text"
              value={newValue}
              onChange={(e) => setNewValue(e.target.value)}
              className="flex-1 input font-mono text-xs"
              placeholder="value"
              onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
            />
            <button
              onClick={handleAdd}
              disabled={!newKey.trim() || !newValue.trim()}
              className="p-1.5 text-accent-green hover:bg-accent-green/10 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center justify-between pt-2">
            <p className="text-xs text-[var(--color-muted)]">
              These will be available as environment variables in the sandbox.
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".env,.env.local,.env.development,.env.production"
              onChange={handleFileUpload}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center gap-1.5 text-xs text-accent-cyan hover:text-accent-cyan/80 transition-colors"
            >
              <Upload className="w-3 h-3" />
              Load .env
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
