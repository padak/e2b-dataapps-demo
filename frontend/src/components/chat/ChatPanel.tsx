import { MessageSquare, Wifi, WifiOff } from 'lucide-react';
import { ChatState } from '../../types/chat';
import MessageList from './MessageList';
import ChatInput from './ChatInput';

interface ChatPanelProps {
  chatState: ChatState;
  onSendMessage: (message: string) => void;
  title?: string;
}

export default function ChatPanel({
  chatState,
  onSendMessage,
  title = 'App Builder Chat'
}: ChatPanelProps) {
  const { messages, isLoading, isConnected, error } = chatState;

  return (
    <div className="flex flex-col h-full bg-[var(--color-bg)]">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-accent-cyan" />
            <h2 className="text-lg font-semibold text-[var(--color-text)]">{title}</h2>
          </div>

          {/* Connection Status */}
          <div className="flex items-center gap-2">
            {isConnected ? (
              <div className="flex items-center gap-1.5 text-xs text-accent-green">
                <Wifi className="w-4 h-4" />
                <span>Connected</span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 text-xs text-[var(--color-muted)]">
                <WifiOff className="w-4 h-4" />
                <span>Disconnected</span>
              </div>
            )}
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="mt-2 px-3 py-2 rounded-lg bg-accent-red/10 border border-accent-red/20 text-accent-red text-sm">
            {error}
          </div>
        )}
      </div>

      {/* Messages */}
      <MessageList messages={messages} />

      {/* Input */}
      <ChatInput
        onSend={onSendMessage}
        isLoading={isLoading}
        disabled={!isConnected}
      />
    </div>
  );
}
