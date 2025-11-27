import { useState } from 'react';
import { Monitor, Code2, Terminal, RefreshCw, ExternalLink, Zap, Cloud } from 'lucide-react';
import PreviewIframe from './PreviewIframe';
import CodeView, { CodeFile } from './CodeView';
import ConsoleOutput, { ConsoleLog } from './ConsoleOutput';

type TabType = 'preview' | 'code' | 'console';

interface PreviewPanelProps {
  previewUrl?: string;
  codeFiles?: CodeFile[];
  consoleLogs?: ConsoleLog[];
  onClearConsole?: () => void;
}

function EmptyPreview() {
  return (
    <div className="h-full flex flex-col items-center justify-center bg-[var(--color-bg)]/30 text-[var(--color-muted)]">
      <div className="relative mb-6">
        {/* Decorative elements */}
        <div className="absolute -inset-8 opacity-20">
          <div className="absolute top-0 left-1/4 w-1 h-1 rounded-full bg-accent-cyan" />
          <div className="absolute top-1/4 right-0 w-1.5 h-1.5 rounded-full bg-accent-green" />
          <div className="absolute bottom-1/4 left-0 w-1 h-1 rounded-full bg-accent-purple" />
          <div className="absolute bottom-0 right-1/4 w-2 h-2 rounded-full bg-accent-orange" />
        </div>

        {/* Main icon */}
        <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-[var(--color-surface)] to-[var(--color-bg)] border border-[var(--color-border)] flex items-center justify-center">
          <Monitor className="w-10 h-10 text-[var(--color-muted)]" />
        </div>
      </div>

      <h3 className="text-lg font-display font-semibold text-[var(--color-text)] mb-2">
        No Preview Available
      </h3>
      <p className="text-sm text-[var(--color-muted)] text-center max-w-xs mb-6">
        Build and run your app to see it running here.
      </p>

      {/* Feature highlights */}
      <div className="flex flex-col gap-2 text-xs">
        <div className="flex items-center gap-2 text-[var(--color-muted)]">
          <Zap className="w-3.5 h-3.5 text-accent-cyan" />
          <span>Live preview with hot reload</span>
        </div>
        <div className="flex items-center gap-2 text-[var(--color-muted)]">
          <Cloud className="w-3.5 h-3.5 text-accent-green" />
          <span>Fully isolated environment</span>
        </div>
      </div>
    </div>
  );
}

export default function PreviewPanel({
  previewUrl,
  codeFiles = [],
  consoleLogs = [],
  onClearConsole,
}: PreviewPanelProps) {
  const [activeTab, setActiveTab] = useState<TabType>('preview');
  const [refreshKey, setRefreshKey] = useState(0);

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
  };

  const tabs: { id: TabType; label: string; icon: typeof Monitor; count?: number }[] = [
    { id: 'preview', label: 'Preview', icon: Monitor },
    { id: 'code', label: 'Code', icon: Code2, count: codeFiles.length },
    { id: 'console', label: 'Console', icon: Terminal, count: consoleLogs.length },
  ];

  return (
    <div className="h-full flex flex-col">
      {/* Tab bar */}
      <div className="flex items-center border-b border-[var(--color-border)] bg-[var(--color-bg)]/50">
        {tabs.map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-accent-cyan text-accent-cyan'
                  : 'border-transparent text-[var(--color-muted)] hover:text-[var(--color-text)]'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span className="font-mono text-sm">{tab.label}</span>
              {tab.count !== undefined && tab.count > 0 && (
                <span className="px-1.5 py-0.5 rounded text-xs bg-[var(--color-border)] text-[var(--color-muted)]">
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}

        <div className="flex-1" />

        {/* Action buttons */}
        {activeTab === 'preview' && previewUrl && (
          <>
            <button
              onClick={handleRefresh}
              className="p-2 mr-2 text-[var(--color-muted)] hover:text-accent-cyan transition-colors rounded hover:bg-accent-cyan/10"
              title="Refresh preview"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <a
              href={previewUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 mr-2 rounded text-xs text-accent-cyan hover:bg-accent-cyan/10 transition-colors"
            >
              <ExternalLink className="w-3 h-3" />
              Open in new tab
            </a>
          </>
        )}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'preview' && (
          previewUrl ? (
            <PreviewIframe url={previewUrl} refreshKey={refreshKey} />
          ) : (
            <EmptyPreview />
          )
        )}

        {activeTab === 'code' && (
          <CodeView files={codeFiles} />
        )}

        {activeTab === 'console' && (
          <ConsoleOutput logs={consoleLogs} onClear={onClearConsole} />
        )}
      </div>
    </div>
  );
}
