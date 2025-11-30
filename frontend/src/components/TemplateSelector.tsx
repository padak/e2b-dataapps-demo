import { ChevronDown, Layers, Zap, Clock } from 'lucide-react';
import { TEMPLATES } from '../types';

interface TemplateSelectorProps {
  value: string;
  onChange: (value: string) => void;
}

export default function TemplateSelector({ value, onChange }: TemplateSelectorProps) {
  const selectedTemplate = TEMPLATES.find((t) => t.id === value) || TEMPLATES[0];

  return (
    <div className="space-y-2">
      <label className="flex items-center gap-2 text-sm font-medium text-[var(--color-text)]">
        <Layers className="w-4 h-4 text-accent-cyan" />
        Sandbox Template
      </label>

      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full appearance-none bg-[var(--color-bg)] border border-[var(--color-border)] rounded-lg px-4 py-2.5 pr-10 text-[var(--color-text)] font-mono text-sm focus:outline-none focus:border-accent-cyan focus:ring-1 focus:ring-accent-cyan/30 cursor-pointer"
        >
          {TEMPLATES.map((template) => (
            <option key={template.id} value={template.id}>
              {template.name}
            </option>
          ))}
        </select>
        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-muted)] pointer-events-none" />
      </div>

      {/* Template info */}
      <div className="flex items-start gap-3 p-3 rounded-lg bg-[var(--color-bg)]/50 border border-[var(--color-border)]/50">
        <div
          className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
            selectedTemplate.id
              ? 'bg-accent-green/10 text-accent-green'
              : 'bg-accent-orange/10 text-accent-orange'
          }`}
        >
          {selectedTemplate.id ? (
            <Zap className="w-4 h-4" />
          ) : (
            <Clock className="w-4 h-4" />
          )}
        </div>
        <div className="min-w-0">
          <p className="text-sm text-[var(--color-text)]">{selectedTemplate.description}</p>
          {selectedTemplate.preInstalled.length > 0 && (
            <p className="text-xs text-[var(--color-muted)] mt-1">
              Pre-installed:{' '}
              <span className="text-accent-cyan">
                {selectedTemplate.preInstalled.join(', ')}
              </span>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
