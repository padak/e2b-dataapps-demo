import { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Zap,
  Loader2,
  RotateCcw,
  PanelLeftClose,
  PanelLeft,
  Play,
} from 'lucide-react';

import ChatPanel from './components/chat/ChatPanel';
import PreviewPanel from './components/preview/PreviewPanel';
import ThemeToggle from './components/ThemeToggle';
import { useTheme } from './hooks/useTheme';
import { useAppStore } from './lib/store';
import { WebSocketClient } from './lib/websocket';
import { Message, ChatState, ToolUse } from './types/chat';
import { CodeFile } from './components/preview/CodeView';
import { ConsoleLog } from './components/preview/ConsoleOutput';

// Format tool usage into human-readable log message
function formatToolLog(toolName: string, input: any): string {
  // Handle native Claude Code tools
  switch (toolName) {
    // File operations
    case 'Write':
      return `📝 Write: ${input?.file_path || 'file'}`;
    case 'Read':
      return `📖 Read: ${input?.file_path || 'file'}`;
    case 'Edit':
      return `✏️ Edit: ${input?.file_path || 'file'}`;

    // Shell commands
    case 'Bash': {
      const cmd = input?.command || '';
      const truncated = cmd.length > 50 ? cmd.slice(0, 50) + '...' : cmd;
      return `💻 Bash: ${truncated}`;
    }

    // Search
    case 'Glob':
      return `🔍 Glob: ${input?.pattern || '*'}`;
    case 'Grep':
      return `🔎 Grep: "${input?.pattern || ''}" in ${input?.path || '.'}`;

    // Task/Subagents
    case 'Task': {
      const agent = input?.subagent_type || input?.description || 'agent';
      const desc = input?.description ? ` - ${input.description}` : '';
      return `🤖 Task: ${agent}${desc}`;
    }

    // Todo management
    case 'TodoWrite': {
      const todos = input?.todos;
      if (Array.isArray(todos)) {
        const completed = todos.filter((t: any) => t.status === 'completed').length;
        const currentTask = todos.find((t: any) => t.status === 'in_progress');
        const taskPreview = currentTask?.content || todos[0]?.content || '';
        const truncatedTask = taskPreview.length > 40 ? taskPreview.slice(0, 40) + '...' : taskPreview;
        return `📋 Plan: ${truncatedTask} (${completed}/${todos.length} done)`;
      }
      return `📋 TodoWrite: updating plan`;
    }

    // MCP E2B tools
    case 'mcp__e2b__get_preview_url':
      return `🌐 Get preview URL`;
    case 'mcp__e2b__start_dev_server':
      return `🚀 Start dev server`;

    // Legacy MCP sandbox tools (E2B mode)
    case 'mcp__sandbox__sandbox_write_file':
      return `📝 Write: ${input?.file_path || 'file'}`;
    case 'mcp__sandbox__sandbox_read_file':
      return `📖 Read: ${input?.file_path || 'file'}`;
    case 'mcp__sandbox__sandbox_run_command': {
      const cmd = input?.command || '';
      return `💻 Run: ${cmd.length > 50 ? cmd.slice(0, 50) + '...' : cmd}`;
    }
    case 'mcp__sandbox__sandbox_list_files':
      return `📁 List: ${input?.path || '/home/user'}`;
    case 'mcp__sandbox__sandbox_install_packages': {
      const pkgs = input?.packages;
      if (Array.isArray(pkgs)) {
        return `📦 Install: ${pkgs.join(', ')}`;
      }
      return `📦 Install: ${pkgs || 'packages'}`;
    }
    case 'mcp__sandbox__sandbox_get_preview_url':
      return `🌐 Get preview URL`;
    case 'mcp__sandbox__sandbox_start_dev_server':
      return `🚀 Start dev server`;

    default:
      // Clean up any remaining prefixes
      const shortName = toolName
        .replace('mcp__sandbox__sandbox_', '')
        .replace('mcp__e2b__', '')
        .replace('mcp__', '');
      return `🔧 ${shortName}`;
  }
}

export default function AppBuilder() {
  const [theme, setTheme] = useTheme();
  const [wsClient, setWsClient] = useState<WebSocketClient | null>(null);
  const [showChat, setShowChat] = useState(true);
  // Tool uses tracked for future UI display
  const [, setToolUses] = useState<ToolUse[]>([]);
  const [codeFiles, setCodeFiles] = useState<CodeFile[]>([]);
  const [consoleLogs, setConsoleLogs] = useState<ConsoleLog[]>([]);
  const currentMessageRef = useRef<string>('');
  const currentMessageIdRef = useRef<string | null>(null);  // Track current assistant message ID
  // Progress tracking
  const [currentAction, setCurrentAction] = useState<string>('');
  const [toolCount, setToolCount] = useState(0);
  const [startTime, setStartTime] = useState<number | null>(null);

  const {
    messages,
    previewUrl,
    sandboxId,
    isConnected,
    isLoading,
    setSessionId,
    setSandboxId,
    addMessage,
    appendToMessage,
    setPreviewUrl,
    setConnected,
    setLoading,
    reset,
  } = useAppStore();

  // Create chat state object for ChatPanel
  const chatState: ChatState = {
    messages,
    isLoading,
    isConnected,
  };

  // Initialize WebSocket connection with proper StrictMode cleanup
  // Uses ref-based pattern to handle async cleanup race conditions
  useEffect(() => {
    // Track if component is still mounted (handles StrictMode double-mount)
    let mounted = true;
    // Ref to track the current WebSocket client for cleanup
    const wsClientRef: { current: WebSocketClient | null } = { current: null };

    const initSession = async () => {
      try {
        // Check if still mounted before starting
        if (!mounted) return;

        // Create session via API
        const response = await fetch('/api/session', { method: 'POST' });
        if (!response.ok) throw new Error('Failed to create session');

        // Check again after async operation
        if (!mounted) return;

        const data = await response.json();
        const newSessionId = data.session_id;
        setSessionId(newSessionId);

        // Connect WebSocket
        const client = new WebSocketClient(newSessionId);
        wsClientRef.current = client;

        client.onMessage((event) => {
          // Only process events if still mounted
          if (mounted) {
            handleWebSocketEvent(event);
          }
        });

        await client.connect();

        // Check if component unmounted during connection
        if (!mounted) {
          client.disconnect();
          return;
        }

        setWsClient(client);
        setConnected(true);
        addLog('Connected to App Builder', 'info');

      } catch (error) {
        console.error('Failed to initialize session:', error);
        if (mounted) {
          addLog(`Connection error: ${error instanceof Error ? error.message : 'Unknown error'}`, 'stderr');
          setConnected(false);
        }
      }
    };

    initSession();

    // Cleanup function - runs on unmount (including StrictMode remount)
    return () => {
      mounted = false;
      // Disconnect the WebSocket client if it exists
      if (wsClientRef.current) {
        wsClientRef.current.disconnect();
        wsClientRef.current = null;
      }
    };
  }, []);

  // Add console log
  const addLog = useCallback((message: string, type: ConsoleLog['type'] = 'info') => {
    const log: ConsoleLog = {
      id: `log-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      timestamp: Date.now(),
      message,
      type,
    };
    setConsoleLogs(prev => [...prev, log]);
  }, []);

  // Handle WebSocket events
  const handleWebSocketEvent = useCallback((event: any) => {
    switch (event.type) {
      case 'connection':
        setConnected(true);
        addLog(`Session connected: ${event.session_id}`, 'info');
        break;

      case 'sandbox_ready':
        setSandboxId(event.sandbox_id);
        addLog(`Sandbox ready: ${event.sandbox_id}`, 'stdout');
        break;

      case 'chat_received':
        // Message acknowledged, create placeholder for assistant response
        const newMessageId = `msg-${Date.now()}`;
        const assistantMessage: Message = {
          id: newMessageId,
          role: 'assistant',
          content: '',
          timestamp: Date.now(),
        };
        addMessage(assistantMessage);
        currentMessageRef.current = '';
        currentMessageIdRef.current = newMessageId;  // Track this message ID
        setStartTime(Date.now());
        setToolCount(0);
        setCurrentAction('Thinking...');
        break;

      case 'text':
        // Append text to current message (by ID)
        currentMessageRef.current += event.content;
        if (currentMessageIdRef.current) {
          appendToMessage(currentMessageIdRef.current, event.content);
        }
        break;

      case 'tool_use':
        // Track tool usage
        const toolUse: ToolUse = {
          id: `tool-${Date.now()}`,
          name: event.tool,
          status: 'running',
          input: event.input,
        };
        setToolUses(prev => [...prev, toolUse]);
        setToolCount(prev => prev + 1);

        // Generate human-readable log message
        const toolLogMessage = formatToolLog(event.tool, event.input);
        addLog(toolLogMessage, 'info');
        setCurrentAction(toolLogMessage);

        // Track file writes for code preview (native Write tool + legacy MCP tool)
        const isWriteTool = event.tool === 'Write' || event.tool === 'mcp__sandbox__sandbox_write_file';
        if (isWriteTool && event.input) {
          // Handle different possible property names for file path and content
          const filePath = event.input.file_path || event.input.path || event.input.filePath;
          const fileContent = event.input.content || event.input.text;

          console.log('[CodeView] Write tool detected:', {
            tool: event.tool,
            input: event.input,
            filePath,
            hasContent: !!fileContent
          });

          if (filePath && fileContent) {
            setCodeFiles(prev => {
              const existing = prev.findIndex(f => f.path === filePath);
              const newFile: CodeFile = {
                path: filePath,
                content: fileContent,
                language: getLanguageFromPath(filePath),
              };
              if (existing >= 0) {
                const updated = [...prev];
                updated[existing] = newFile;
                return updated;
              }
              console.log('[CodeView] Adding file:', filePath);
              return [...prev, newFile];
            });
          }
        }
        break;

      case 'tool_result':
        // Update tool status
        setToolUses(prev => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last) {
            last.status = 'completed';
            last.output = typeof event.result === 'string'
              ? event.result
              : JSON.stringify(event.result, null, 2);

            // Log command output if available
            if (typeof event.result === 'object' && event.result) {
              const result = event.result as Record<string, unknown>;
              if (result.stdout && typeof result.stdout === 'string') {
                // Truncate long output
                const stdout = result.stdout.trim();
                if (stdout) {
                  const lines = stdout.split('\n');
                  if (lines.length > 5) {
                    addLog(`Output: ${lines.slice(0, 3).join('\n')}...(${lines.length} lines)`, 'stdout');
                  } else {
                    addLog(`Output: ${stdout}`, 'stdout');
                  }
                }
              }
              if (result.stderr && typeof result.stderr === 'string') {
                const stderr = result.stderr.trim();
                if (stderr) {
                  addLog(`Error: ${stderr.slice(0, 200)}`, 'stderr');
                }
              }
              if (result.preview_url || result.url) {
                const url = (result.preview_url || result.url) as string;
                addLog(`Preview: ${url}`, 'stdout');
                setPreviewUrl(url);  // Set preview URL immediately when available
              }
            }
          }
          return updated;
        });
        break;

      case 'done':
        setLoading(false);
        setCurrentAction('');
        if (event.preview_url) {
          setPreviewUrl(event.preview_url);
          addLog(`Preview available: ${event.preview_url}`, 'stdout');
        }
        // Log completion stats
        if (startTime) {
          const duration = ((Date.now() - startTime) / 1000).toFixed(1);
          addLog(`Completed in ${duration}s (${toolCount} operations)`, 'info');
        }
        break;

      case 'error':
        setLoading(false);
        addLog(`Error: ${event.message || 'Unknown error'}`, 'stderr');
        break;

      case 'pong':
        // Keepalive response, ignore
        break;

      default:
        console.log('Unknown event:', event);
    }
  }, [addMessage, appendToMessage, setConnected, setLoading, setPreviewUrl, setSandboxId, addLog, startTime, toolCount]);

  // Send message handler
  const handleSendMessage = useCallback((content: string) => {
    if (!wsClient || !isConnected || !content.trim()) return;

    // Add user message to state
    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: content.trim(),
      timestamp: Date.now(),
    };
    addMessage(userMessage);
    setLoading(true);

    // Clear previous tool uses for new message
    setToolUses([]);

    // Send to backend
    wsClient.send('chat', { message: content.trim() });
  }, [wsClient, isConnected, addMessage, setLoading]);

  // Reset session
  const handleReset = useCallback(async () => {
    if (!wsClient) return;

    reset();
    setCodeFiles([]);
    setConsoleLogs([]);
    setToolUses([]);
    setPreviewUrl(null);
    setSandboxId(null);

    wsClient.send('reset');
    addLog('Session reset', 'info');
  }, [wsClient, reset, setPreviewUrl, setSandboxId, addLog]);

  // Clear console logs
  const handleClearConsole = useCallback(() => {
    setConsoleLogs([]);
  }, []);

  // Get language from file path
  const getLanguageFromPath = (path: string): string => {
    const ext = path.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'tsx':
      case 'ts':
        return 'typescript';
      case 'jsx':
      case 'js':
        return 'javascript';
      case 'css':
        return 'css';
      case 'json':
        return 'json';
      case 'md':
        return 'markdown';
      default:
        return 'text';
    }
  };

  return (
    <div className="min-h-screen h-screen flex flex-col theme-bg grid-bg noise-overlay overflow-hidden">
      {/* Header */}
      <header className="border-b border-[var(--color-border)] theme-surface flex-shrink-0 z-50 backdrop-blur-sm bg-[var(--color-surface)]/90">
        <div className="max-w-[2000px] mx-auto px-4 py-3">
          <div className="flex items-center justify-between gap-4">
            {/* Logo & Title */}
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-accent-purple to-accent-cyan flex items-center justify-center">
                  <Zap className="w-5 h-5 text-white" />
                </div>
              </div>
              <div className="hidden sm:block">
                <h1 className="text-lg font-display font-bold text-[var(--color-bright)]">
                  E2B <span className="gradient-text">App Builder</span>
                </h1>
                <p className="text-xs text-[var(--color-muted)] font-mono">
                  AI-powered Next.js development
                </p>
              </div>
            </div>

            {/* Center Controls */}
            <div className="flex items-center gap-3">
              {/* Connection Status */}
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full theme-surface border border-[var(--color-border)]">
                <div
                  className={`w-2 h-2 rounded-full ${
                    isConnected
                      ? 'bg-accent-green status-pulse'
                      : 'bg-[var(--color-muted)]'
                  }`}
                />
                <span className="text-sm font-mono text-[var(--color-text)] hidden sm:inline">
                  {isConnected ? 'Connected' : 'Disconnected'}
                </span>
                {sandboxId && (
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(sandboxId);
                      addLog(`Copied sandbox ID: ${sandboxId}`, 'info');
                    }}
                    className="text-xs font-mono text-[var(--color-muted)] hidden md:inline border-l border-[var(--color-border)] pl-2 ml-1 hover:text-accent-cyan cursor-pointer"
                    title={`Click to copy: ${sandboxId}`}
                  >
                    {sandboxId}
                  </button>
                )}
              </div>

              {/* Loading indicator with progress */}
              {isLoading && (
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-accent-cyan/10 border border-accent-cyan/30">
                  <Loader2 className="w-4 h-4 text-accent-cyan animate-spin" />
                  <div className="hidden sm:flex flex-col">
                    <span className="text-sm font-mono text-accent-cyan">
                      {currentAction || 'Building...'}
                    </span>
                    {toolCount > 0 && (
                      <span className="text-xs font-mono text-[var(--color-muted)]">
                        {toolCount} operations
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Right Controls */}
            <div className="flex items-center gap-2">
              {/* Reset Button */}
              <button
                onClick={handleReset}
                className="p-2 rounded-lg border border-[var(--color-border)] text-[var(--color-muted)] hover:text-[var(--color-text)] hover:border-[var(--color-muted)] transition-colors"
                title="Reset session"
              >
                <RotateCcw className="w-5 h-5" />
              </button>

              {/* Streamlit Launcher Link */}
              <Link
                to="/streamlit"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--color-border)] text-[var(--color-muted)] hover:text-[var(--color-text)] hover:border-[var(--color-muted)] transition-colors text-sm"
                title="Streamlit Launcher"
              >
                <Play className="w-4 h-4" />
                <span className="hidden sm:inline">Streamlit</span>
              </Link>

              {/* Theme Toggle */}
              <ThemeToggle theme={theme} setTheme={setTheme} />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 min-h-0 flex">
        {/* Chat Panel */}
        <AnimatePresence>
          {showChat && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: '40%', opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="h-full border-r border-[var(--color-border)] flex flex-col min-w-[300px] max-w-[600px]"
            >
              <ChatPanel
                chatState={chatState}
                onSendMessage={handleSendMessage}
                title="App Builder"
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Toggle Chat Button (when hidden) */}
        {!showChat && (
          <button
            onClick={() => setShowChat(true)}
            className="absolute left-4 top-1/2 -translate-y-1/2 z-10 p-2 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-muted)] hover:text-[var(--color-text)] transition-colors shadow-lg"
            title="Show chat"
          >
            <PanelLeft className="w-5 h-5" />
          </button>
        )}

        {/* Preview Panel */}
        <div className="flex-1 h-full flex flex-col min-w-0">
          {/* Toggle Chat Button */}
          <div className="flex items-center px-2 py-1 border-b border-[var(--color-border)] bg-[var(--color-surface)]/50">
            <button
              onClick={() => setShowChat(!showChat)}
              className="p-1.5 rounded text-[var(--color-muted)] hover:text-[var(--color-text)] transition-colors"
              title={showChat ? 'Hide chat' : 'Show chat'}
            >
              {showChat ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeft className="w-4 h-4" />}
            </button>
          </div>

          {/* Preview Content */}
          <div className="flex-1 min-h-0">
            <PreviewPanel
              previewUrl={previewUrl || undefined}
              codeFiles={codeFiles}
              consoleLogs={consoleLogs}
              onClearConsole={handleClearConsole}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
