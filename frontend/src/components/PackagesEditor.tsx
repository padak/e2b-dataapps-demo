import { useState } from 'react';
import { ChevronRight, Plus, X, Package, Sparkles } from 'lucide-react';

interface PackagesEditorProps {
  packages: string[];
  onChange: (packages: string[]) => void;
  detectedPackages: string[];
}

export default function PackagesEditor({
  packages,
  onChange,
  detectedPackages,
}: PackagesEditorProps) {
  const [expanded, setExpanded] = useState(false);
  const [newPackage, setNewPackage] = useState('');

  const handleAdd = () => {
    const pkg = newPackage.trim().toLowerCase();
    if (pkg && !packages.includes(pkg)) {
      onChange([...packages, pkg]);
      setNewPackage('');
    }
  };

  const handleRemove = (pkg: string) => {
    onChange(packages.filter((p) => p !== pkg));
  };

  const handleAddDetected = (pkg: string) => {
    if (!packages.includes(pkg)) {
      onChange([...packages, pkg]);
    }
  };

  // Filter detected packages that aren't already in the list
  const suggestedPackages = detectedPackages.filter((p) => !packages.includes(p));

  return (
    <div className="space-y-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-sm font-medium text-[var(--color-text)] w-full hover:text-accent-cyan transition-colors"
      >
        <ChevronRight className={`w-4 h-4 transition-transform ${expanded ? 'rotate-90' : ''}`} />
        <Package className="w-4 h-4 text-accent-green" />
        <span>Additional Packages</span>
        <span className="ml-auto text-xs text-[var(--color-muted)]">
          {packages.length} extra
        </span>
      </button>

      {expanded && (
        <div className="ml-6 space-y-3">
          {/* Auto-detected packages info */}
          {suggestedPackages.length > 0 && (
            <div className="p-2 rounded-lg bg-accent-cyan/5 border border-accent-cyan/20">
              <div className="flex items-center gap-2 text-xs text-accent-cyan mb-2">
                <Sparkles className="w-3 h-3" />
                <span>Auto-detected from imports</span>
              </div>
              <div className="flex flex-wrap gap-1">
                {suggestedPackages.map((pkg) => (
                  <button
                    key={pkg}
                    onClick={() => handleAddDetected(pkg)}
                    className="px-2 py-0.5 text-xs rounded bg-accent-cyan/10 text-accent-cyan hover:bg-accent-cyan/20 transition-colors"
                  >
                    + {pkg}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Added packages */}
          {packages.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {packages.map((pkg) => (
                <span
                  key={pkg}
                  className="flex items-center gap-1 px-2 py-1 text-xs rounded-full
                    bg-accent-green/10 text-accent-green border border-accent-green/30"
                >
                  {pkg}
                  <button
                    onClick={() => handleRemove(pkg)}
                    className="hover:text-accent-red transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          )}

          {/* Add new package */}
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={newPackage}
              onChange={(e) => setNewPackage(e.target.value)}
              className="flex-1 input font-mono text-xs"
              placeholder="package-name (e.g., requests, beautifulsoup4)"
              onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
            />
            <button
              onClick={handleAdd}
              disabled={!newPackage.trim()}
              className="p-1.5 text-accent-green hover:bg-accent-green/10 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>

          <p className="text-xs text-[var(--color-muted)]">
            Installed via <code className="text-accent-cyan">uv pip install</code> before running.
          </p>
        </div>
      )}
    </div>
  );
}
