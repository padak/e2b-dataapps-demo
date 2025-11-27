import { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { Loader2, Monitor, AlertCircle, Cloud, Zap, RefreshCw } from 'lucide-react';
import { SandboxState } from '../types';

interface SandboxPreviewProps {
  url?: string;
  status: SandboxState['status'];
}

function RunningPreview({ url }: { url: string }) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [isReloading, setIsReloading] = useState(false);

  const handleReload = () => {
    setIsReloading(true);
    if (iframeRef.current) {
      iframeRef.current.src = url;
    }
    // Reset reloading state after animation
    setTimeout(() => setIsReloading(false), 1000);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="w-full h-full relative"
    >
      {/* Reload button */}
      <button
        onClick={handleReload}
        className="absolute top-3 right-3 z-10 p-2 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-muted)] hover:text-accent-cyan hover:border-accent-cyan/50 transition-colors shadow-md"
        title="Reload preview"
      >
        <RefreshCw className={`w-4 h-4 ${isReloading ? 'animate-spin' : ''}`} />
      </button>

      <iframe
        ref={iframeRef}
        src={url}
        className="w-full h-full border-0 bg-white"
        title="Streamlit App Preview"
        sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
      />
    </motion.div>
  );
}

export default function SandboxPreview({ url, status }: SandboxPreviewProps) {
  // Show loading state
  if (['creating', 'installing', 'uploading', 'starting'].includes(status)) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-[var(--color-bg)]/30 text-[var(--color-muted)]">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="relative"
        >
          {/* Animated background glow */}
          <div className="absolute inset-0 rounded-full bg-accent-cyan/20 blur-xl animate-pulse-slow" />

          {/* Spinner container */}
          <div className="relative w-20 h-20 rounded-full border-2 border-[var(--color-border)] flex items-center justify-center">
            <Loader2 className="w-8 h-8 text-accent-cyan animate-spin" />
          </div>

          {/* Orbiting dots */}
          <motion.div
            className="absolute inset-0"
            animate={{ rotate: 360 }}
            transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
          >
            <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1 w-2 h-2 rounded-full bg-accent-cyan" />
          </motion.div>
          <motion.div
            className="absolute inset-0"
            animate={{ rotate: 360 }}
            transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
          >
            <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1 w-1.5 h-1.5 rounded-full bg-accent-green" />
          </motion.div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="mt-6 text-center"
        >
          <p className="text-[var(--color-text)] font-medium mb-1">
            {status === 'creating' && 'Creating sandbox environment...'}
            {status === 'installing' && 'Installing dependencies...'}
            {status === 'uploading' && 'Uploading your code...'}
            {status === 'starting' && 'Starting Streamlit server...'}
          </p>
          <p className="text-sm text-[var(--color-muted)]">This usually takes 4-12 seconds</p>
        </motion.div>

        {/* Progress indicators */}
        <div className="flex items-center gap-3 mt-6">
          {['creating', 'installing', 'uploading', 'starting'].map((step, index) => {
            const currentIndex = ['creating', 'installing', 'uploading', 'starting'].indexOf(
              status
            );
            const isComplete = index < currentIndex;
            const isCurrent = step === status;

            return (
              <div key={step} className="flex items-center gap-3">
                <motion.div
                  initial={false}
                  animate={{
                    scale: isCurrent ? 1.2 : 1,
                    backgroundColor: isComplete
                      ? '#3fb950'
                      : isCurrent
                      ? '#39c5cf'
                      : '#1c2128',
                  }}
                  className="w-2 h-2 rounded-full"
                />
                {index < 3 && (
                  <div
                    className={`w-8 h-0.5 ${
                      isComplete ? 'bg-accent-green' : 'bg-[var(--color-border)]'
                    }`}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // Show error state
  if (status === 'error') {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-[var(--color-bg)]/30 text-[var(--color-muted)]">
        <div className="w-16 h-16 rounded-full bg-accent-red/10 border border-accent-red/30 flex items-center justify-center mb-4">
          <AlertCircle className="w-8 h-8 text-accent-red" />
        </div>
        <p className="text-accent-red font-medium mb-1">Something went wrong</p>
        <p className="text-sm text-[var(--color-muted)]">Check the logs for details</p>
      </div>
    );
  }

  // Show running preview
  if (status === 'running' && url) {
    return <RunningPreview url={url} />;
  }

  // Default idle state
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
        Write your Streamlit code in the editor and click{' '}
        <span className="text-accent-green font-medium">Launch</span> to see it running here.
      </p>

      {/* Feature highlights */}
      <div className="flex flex-col gap-2 text-xs">
        <div className="flex items-center gap-2 text-[var(--color-muted)]">
          <Zap className="w-3.5 h-3.5 text-accent-cyan" />
          <span>Instant sandbox creation (~4s with template)</span>
        </div>
        <div className="flex items-center gap-2 text-[var(--color-muted)]">
          <Cloud className="w-3.5 h-3.5 text-accent-green" />
          <span>Fully isolated environment</span>
        </div>
      </div>
    </div>
  );
}
