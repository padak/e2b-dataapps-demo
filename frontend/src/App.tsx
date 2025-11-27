import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Play,
  Square,
  Settings,
  Zap,
  Monitor,
  Terminal,
  Code2,
  ExternalLink,
  Loader2,
  Maximize2,
  Minimize2,
  PanelLeftClose,
  PanelLeft,
  ChevronDown,
} from 'lucide-react';

import CodeEditor from './components/CodeEditor';
import LogTerminal from './components/LogTerminal';
import SandboxPreview from './components/SandboxPreview';
import TemplateSelector from './components/TemplateSelector';
import ExampleSelector from './components/ExampleSelector';
import ThemeToggle from './components/ThemeToggle';
import ScriptFilesSelector from './components/ScriptFilesSelector';
import EnvVarsEditor from './components/EnvVarsEditor';
import PackagesEditor from './components/PackagesEditor';

import { useTheme } from './hooks/useTheme';
import { SandboxState, LogEntry, EXAMPLE_SCRIPTS } from './types';

// Common mapping of import names to pip packages
const IMPORT_TO_PIP: Record<string, string> = {
  streamlit: 'streamlit',
  pandas: 'pandas',
  plotly: 'plotly',
  httpx: 'httpx',
  numpy: 'numpy',
  matplotlib: 'matplotlib',
  seaborn: 'seaborn',
  sklearn: 'scikit-learn',
  scipy: 'scipy',
  requests: 'requests',
  altair: 'altair',
  bokeh: 'bokeh',
  pydantic: 'pydantic',
};

function extractDependencies(code: string): string[] {
  const deps = new Set<string>();

  for (const line of code.split('\n')) {
    const trimmed = line.trim();
    if (trimmed.startsWith('import ') || trimmed.startsWith('from ')) {
      let module: string;
      if (trimmed.startsWith('from ')) {
        module = trimmed.split(' ')[1].split('.')[0];
      } else {
        module = trimmed.split(' ')[1].split('.')[0];
      }

      if (IMPORT_TO_PIP[module]) {
        deps.add(IMPORT_TO_PIP[module]);
      }
    }
  }

  return Array.from(deps).sort();
}

const STATUS_LABELS: Record<SandboxState['status'], string> = {
  idle: 'Ready',
  creating: 'Creating sandbox...',
  installing: 'Installing dependencies...',
  uploading: 'Uploading script...',
  starting: 'Starting Streamlit...',
  running: 'Running',
  error: 'Error',
  stopped: 'Stopped',
};

const STATUS_COLORS: Record<SandboxState['status'], string> = {
  idle: 'bg-[var(--color-muted)]',
  creating: 'bg-accent-orange',
  installing: 'bg-accent-orange',
  uploading: 'bg-accent-orange',
  starting: 'bg-accent-orange',
  running: 'bg-accent-green',
  error: 'bg-accent-red',
  stopped: 'bg-[var(--color-muted)]',
};

export default function App() {
  const [theme, setTheme] = useTheme();
  const [code, setCode] = useState(EXAMPLE_SCRIPTS['Hello World']);
  const [template, setTemplate] = useState('');
  const [port] = useState(8501);
  const [envVars, setEnvVars] = useState<Record<string, string>>({});
  const [extraPackages, setExtraPackages] = useState<string[]>([]);

  const [sandboxState, setSandboxState] = useState<SandboxState>({ status: 'idle' });
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [showSettings, setShowSettings] = useState(false);
  const [activeTab, setActiveTab] = useState<'preview' | 'logs'>('logs');
  const [previewExpanded, setPreviewExpanded] = useState(false);
  const [showEditor, setShowEditor] = useState(true);

  const eventSourceRef = useRef<EventSource | null>(null);

  // Detect dependencies from code
  const detectedPackages = useMemo(() => extractDependencies(code), [code]);

  const addLog = useCallback((message: string, level: LogEntry['level'] = 'info') => {
    const entry: LogEntry = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      timestamp: Date.now(),
      message,
      level,
    };
    setLogs((prev) => [...prev, entry]);
  }, []);

  const handleLaunch = useCallback(async () => {
    // Clear previous state
    setLogs([]);
    setSandboxState({ status: 'creating' });

    addLog('Initializing E2B sandbox...', 'info');

    try {
      // Close any existing connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      // Combine detected and extra packages
      const allPackages = [...new Set([...detectedPackages, ...extraPackages])];

      // Start SSE connection for streaming logs
      const params = new URLSearchParams({
        template: template,
        port: port.toString(),
      });

      const response = await fetch(`/api/launch?${params}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code,
          envVars: Object.keys(envVars).length > 0 ? envVars : undefined,
          packages: allPackages.length > 0 ? allPackages : undefined,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }

      // Handle SSE stream
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error('No response body');

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              handleStreamEvent(data);
            } catch {
              // Ignore parse errors for incomplete chunks
            }
          }
        }
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      addLog(`Error: ${message}`, 'error');
      setSandboxState({ status: 'error', error: message });
    }
  }, [code, template, port, envVars, extraPackages, detectedPackages, addLog]);

  const handleStreamEvent = useCallback(
    (data: { type: string; message?: string; status?: string; url?: string; sandboxId?: string }) => {
      switch (data.type) {
        case 'log':
          addLog(data.message || '', (data.status as LogEntry['level']) || 'info');
          break;
        case 'status':
          setSandboxState((prev) => ({
            ...prev,
            status: data.status as SandboxState['status'],
          }));
          break;
        case 'ready':
          setSandboxState({
            status: 'running',
            publicUrl: data.url,
            sandboxId: data.sandboxId,
          });
          addLog(`Streamlit running at ${data.url}`, 'success');
          setActiveTab('preview');
          break;
        case 'error':
          addLog(data.message || 'Unknown error', 'error');
          setSandboxState({ status: 'error', error: data.message });
          break;
      }
    },
    [addLog]
  );

  const handleStop = useCallback(async () => {
    if (!sandboxState.sandboxId) return;

    try {
      await fetch(`/api/sandbox/${sandboxState.sandboxId}`, { method: 'DELETE' });
      addLog('Sandbox stopped', 'info');
      setSandboxState({ status: 'stopped' });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      addLog(`Error stopping sandbox: ${message}`, 'error');
    }
  }, [sandboxState.sandboxId, addLog]);

  const handleCodeSelect = useCallback((newCode: string) => {
    setCode(newCode);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const isRunning = sandboxState.status === 'running';
  const isLoading = ['creating', 'installing', 'uploading', 'starting'].includes(sandboxState.status);

  return (
    <div className="min-h-screen h-screen flex flex-col theme-bg grid-bg noise-overlay overflow-hidden">
      {/* Header */}
      <header className="border-b border-[var(--color-border)] theme-surface flex-shrink-0 z-50 backdrop-blur-sm bg-[var(--color-surface)]/90">
        <div className="max-w-[2000px] mx-auto px-4 py-3">
          <div className="flex items-center justify-between gap-4">
            {/* Logo & Title */}
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-accent-cyan to-accent-green flex items-center justify-center">
                  <Zap className="w-5 h-5 text-white" />
                </div>
              </div>
              <div className="hidden sm:block">
                <h1 className="text-lg font-display font-bold text-[var(--color-bright)]">
                  E2B <span className="gradient-text">Streamlit</span>
                </h1>
                <p className="text-xs text-[var(--color-muted)] font-mono">
                  Isolated sandbox runner
                </p>
              </div>
            </div>

            {/* Center Controls */}
            <div className="flex items-center gap-3">
              {/* Status Badge */}
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full theme-surface border border-[var(--color-border)]">
                <div
                  className={`w-2 h-2 rounded-full ${STATUS_COLORS[sandboxState.status]} ${
                    isLoading ? 'animate-pulse' : isRunning ? 'status-pulse' : ''
                  }`}
                />
                <span className="text-sm font-mono text-[var(--color-text)] hidden sm:inline">
                  {STATUS_LABELS[sandboxState.status]}
                </span>
              </div>

              {/* Launch/Stop Button */}
              {isRunning ? (
                <button
                  onClick={handleStop}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-accent-red/20 border border-accent-red text-accent-red hover:bg-accent-red/30 transition-colors font-medium"
                >
                  <Square className="w-4 h-4" />
                  <span className="hidden sm:inline">Stop</span>
                </button>
              ) : (
                <button
                  onClick={handleLaunch}
                  disabled={isLoading}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-accent-green text-white hover:bg-accent-green/90 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed btn-glow"
                >
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Play className="w-4 h-4" />
                  )}
                  <span className="hidden sm:inline">{isLoading ? 'Launching...' : 'Launch'}</span>
                </button>
              )}
            </div>

            {/* Right Controls */}
            <div className="flex items-center gap-2">
              {/* Settings Toggle */}
              <button
                onClick={() => setShowSettings(!showSettings)}
                className={`p-2 rounded-lg border transition-colors ${
                  showSettings
                    ? 'bg-accent-cyan/10 border-accent-cyan text-accent-cyan'
                    : 'border-[var(--color-border)] text-[var(--color-muted)] hover:text-[var(--color-text)] hover:border-[var(--color-muted)]'
                }`}
                title="Settings"
              >
                <Settings className="w-5 h-5" />
              </button>

              {/* Theme Toggle */}
              <ThemeToggle theme={theme} setTheme={setTheme} />
            </div>
          </div>

          {/* Settings Panel */}
          <AnimatePresence>
            {showSettings && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <div className="pt-4 mt-4 border-t border-[var(--color-border)] grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <TemplateSelector value={template} onChange={setTemplate} />
                  <ExampleSelector onSelect={handleCodeSelect} />
                  <div className="space-y-3">
                    <ScriptFilesSelector onSelect={handleCodeSelect} />
                    <EnvVarsEditor envVars={envVars} onChange={setEnvVars} />
                  </div>
                  <PackagesEditor
                    packages={extraPackages}
                    onChange={setExtraPackages}
                    detectedPackages={detectedPackages}
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[2000px] mx-auto p-4 flex-1 min-h-0">
        <div
          className={`grid gap-4 h-full transition-all duration-300 ${
            previewExpanded
              ? 'grid-cols-1'
              : showEditor
              ? 'grid-cols-1 lg:grid-cols-2'
              : 'grid-cols-1'
          }`}
        >
          {/* Left Panel - Code Editor */}
          {showEditor && !previewExpanded && (
            <div className="flex flex-col rounded-xl border border-[var(--color-border)] theme-surface overflow-hidden shadow-sm">
              <div className="flex items-center gap-2 px-4 py-3 border-b border-[var(--color-border)] bg-[var(--color-bg)]/50">
                <Code2 className="w-4 h-4 text-accent-cyan" />
                <span className="font-mono text-sm text-[var(--color-text)]">app.py</span>
                <div className="flex-1" />
                <span className="text-xs text-[var(--color-muted)] font-mono">
                  {code.split('\n').length} lines
                </span>
              </div>
              <div className="flex-1 overflow-hidden">
                <CodeEditor value={code} onChange={setCode} />
              </div>
            </div>
          )}

          {/* Right Panel - Preview/Logs */}
          <div
            className={`flex flex-col rounded-xl border border-[var(--color-border)] theme-surface overflow-hidden shadow-sm ${
              previewExpanded ? 'col-span-full' : ''
            }`}
          >
            {/* Tabs */}
            <div className="flex items-center border-b border-[var(--color-border)] bg-[var(--color-bg)]/50">
              {/* Toggle Editor Button (when expanded) */}
              {!previewExpanded && (
                <button
                  onClick={() => setShowEditor(!showEditor)}
                  className="p-3 text-[var(--color-muted)] hover:text-[var(--color-text)] transition-colors lg:hidden"
                  title={showEditor ? 'Hide editor' : 'Show editor'}
                >
                  {showEditor ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeft className="w-4 h-4" />}
                </button>
              )}

              <button
                onClick={() => setActiveTab('preview')}
                className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${
                  activeTab === 'preview'
                    ? 'border-accent-cyan text-accent-cyan'
                    : 'border-transparent text-[var(--color-muted)] hover:text-[var(--color-text)]'
                }`}
              >
                <Monitor className="w-4 h-4" />
                <span className="font-mono text-sm">Preview</span>
              </button>
              <button
                onClick={() => setActiveTab('logs')}
                className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${
                  activeTab === 'logs'
                    ? 'border-accent-cyan text-accent-cyan'
                    : 'border-transparent text-[var(--color-muted)] hover:text-[var(--color-text)]'
                }`}
              >
                <Terminal className="w-4 h-4" />
                <span className="font-mono text-sm">Logs</span>
                {logs.length > 0 && (
                  <span className="px-1.5 py-0.5 rounded text-xs bg-[var(--color-border)] text-[var(--color-muted)]">
                    {logs.length}
                  </span>
                )}
              </button>

              <div className="flex-1" />

              {/* Expand/Collapse Button */}
              <button
                onClick={() => setPreviewExpanded(!previewExpanded)}
                className="p-2 mr-2 text-[var(--color-muted)] hover:text-[var(--color-text)] transition-colors"
                title={previewExpanded ? 'Collapse' : 'Expand'}
              >
                {previewExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
              </button>

              {sandboxState.publicUrl && (
                <a
                  href={sandboxState.publicUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 px-3 py-1.5 mr-2 rounded text-xs text-accent-cyan hover:bg-accent-cyan/10 transition-colors"
                >
                  <ExternalLink className="w-3 h-3" />
                  Open in new tab
                </a>
              )}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-hidden">
              {activeTab === 'preview' ? (
                <SandboxPreview url={sandboxState.publicUrl} status={sandboxState.status} />
              ) : (
                <LogTerminal logs={logs} />
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
