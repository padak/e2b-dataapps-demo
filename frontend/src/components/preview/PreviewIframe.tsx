import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { AlertCircle } from 'lucide-react';

interface PreviewIframeProps {
  url: string;
  refreshKey?: number;
}

export default function PreviewIframe({ url, refreshKey = 0 }: PreviewIframeProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Reset loading and error states when URL or refreshKey changes
  useEffect(() => {
    setIsLoading(true);
    setHasError(false);
  }, [url, refreshKey]);

  const handleLoad = () => {
    setIsLoading(false);
    setHasError(false);
  };

  const handleError = () => {
    setIsLoading(false);
    setHasError(true);
  };

  return (
    <div className="relative w-full h-full">
      {/* Loading skeleton */}
      {isLoading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 bg-[var(--color-bg)]/50 flex items-center justify-center z-10"
        >
          <div className="flex flex-col items-center gap-3">
            <div className="w-12 h-12 border-3 border-[var(--color-border)] border-t-accent-cyan rounded-full animate-spin" />
            <p className="text-sm text-[var(--color-muted)] font-mono">Loading preview...</p>
          </div>
        </motion.div>
      )}

      {/* Error state */}
      {hasError && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-[var(--color-bg)]/30">
          <div className="w-16 h-16 rounded-full bg-accent-red/10 border border-accent-red/30 flex items-center justify-center mb-4">
            <AlertCircle className="w-8 h-8 text-accent-red" />
          </div>
          <p className="text-accent-red font-medium mb-1">Failed to load preview</p>
          <p className="text-sm text-[var(--color-muted)]">The iframe could not be loaded</p>
        </div>
      )}

      {/* Iframe */}
      <iframe
        key={refreshKey}
        ref={iframeRef}
        src={url}
        className="w-full h-full border-0 bg-white"
        title="App Preview"
        sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
        onLoad={handleLoad}
        onError={handleError}
      />
    </div>
  );
}
