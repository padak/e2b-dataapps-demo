import { useState, useMemo } from 'react';
import { Copy, Check, Code2 } from 'lucide-react';
import FileTree, { FileNode } from './FileTree';

export interface CodeFile {
  path: string;
  content: string;
  language?: string;
}

/**
 * Extract relative path from absolute sandbox path.
 * Handles paths like /private/var/folders/.../app-builder/session-id/app/page.tsx
 * Returns just the project-relative part like app/page.tsx
 */
function getRelativePath(absolutePath: string): string {
  // Look for common project root indicators
  const projectRoots = ['app/', 'components/', 'lib/', 'types/', 'pages/', 'src/', 'public/'];

  for (const root of projectRoots) {
    const idx = absolutePath.indexOf(root);
    if (idx !== -1) {
      return absolutePath.slice(idx);
    }
  }

  // Fallback: look for app-builder session pattern and take everything after it
  const appBuilderMatch = absolutePath.match(/app-builder\/[^/]+\/(.+)$/);
  if (appBuilderMatch) {
    return appBuilderMatch[1];
  }

  // Last resort: just take the filename or last path segments
  const parts = absolutePath.split('/').filter(Boolean);
  if (parts.length <= 3) {
    return parts.join('/');
  }
  return parts.slice(-3).join('/');
}

interface CodeViewProps {
  files: CodeFile[];
}

// Simple syntax highlighting for Python (can be extended)
function highlightPython(code: string): string {
  let highlighted = code;

  // Keywords
  const keywords = [
    'import', 'from', 'def', 'class', 'if', 'else', 'elif', 'for', 'while',
    'in', 'return', 'try', 'except', 'finally', 'with', 'as', 'async', 'await',
    'lambda', 'yield', 'pass', 'break', 'continue', 'raise', 'assert', 'global',
    'nonlocal', 'del', 'and', 'or', 'not', 'is', 'None', 'True', 'False'
  ];

  keywords.forEach(keyword => {
    const regex = new RegExp(`\\b(${keyword})\\b`, 'g');
    highlighted = highlighted.replace(regex, '<span class="text-accent-purple font-semibold">$1</span>');
  });

  // Strings (simple detection)
  highlighted = highlighted.replace(
    /(['"`])(.*?)\1/g,
    '<span class="text-accent-green">$1$2$1</span>'
  );

  // Comments
  highlighted = highlighted.replace(
    /(#.*$)/gm,
    '<span class="text-[var(--color-muted)] italic">$1</span>'
  );

  // Numbers
  highlighted = highlighted.replace(
    /\b(\d+\.?\d*)\b/g,
    '<span class="text-accent-cyan">$1</span>'
  );

  return highlighted;
}

function convertFilesToTree(files: CodeFile[]): { tree: FileNode[], pathMap: Map<string, string> } {
  const tree: FileNode[] = [];
  const folderMap = new Map<string, FileNode>();
  // Map from relative path to original absolute path
  const pathMap = new Map<string, string>();

  files.forEach(file => {
    // Convert to relative path for display
    const relativePath = getRelativePath(file.path);
    pathMap.set(relativePath, file.path);

    const parts = relativePath.split('/').filter(Boolean);
    let currentPath = '';
    let currentLevel = tree;

    parts.forEach((part, index) => {
      currentPath = currentPath ? `${currentPath}/${part}` : part;
      const isFile = index === parts.length - 1;

      if (isFile) {
        currentLevel.push({
          name: part,
          path: relativePath, // Use relative path for display
          type: 'file',
        });
      } else {
        let folder = folderMap.get(currentPath);
        if (!folder) {
          folder = {
            name: part,
            path: currentPath,
            type: 'folder',
            children: [],
          };
          folderMap.set(currentPath, folder);
          currentLevel.push(folder);
        }
        currentLevel = folder.children!;
      }
    });
  });

  return { tree, pathMap };
}

export default function CodeView({ files }: CodeViewProps) {
  // Convert files to tree structure with relative paths
  const { tree: fileTree, pathMap } = useMemo(() => convertFilesToTree(files), [files]);

  // Get initial selected file (first file's relative path)
  const firstRelativePath = files.length > 0 ? getRelativePath(files[0].path) : '';
  const [selectedFile, setSelectedFile] = useState<string>(firstRelativePath);
  const [copiedFile, setCopiedFile] = useState<string | null>(null);

  // Find current file by looking up the absolute path from the relative path
  const absolutePath = pathMap.get(selectedFile);
  const currentFile = files.find(f => f.path === absolutePath);
  const displayPath = selectedFile; // This is already the relative path

  const handleCopy = async (content: string, filePath: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedFile(filePath);
      setTimeout(() => setCopiedFile(null), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  if (files.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-[var(--color-bg)]/30 text-[var(--color-muted)]">
        <Code2 className="w-12 h-12 mb-3 opacity-20" />
        <p className="text-center text-sm">
          No code files available.
          <br />
          Generated files will appear here.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex">
      {/* File tree sidebar - scrollable */}
      <div className="w-56 min-w-[14rem] border-r border-[var(--color-border)] bg-[var(--color-surface)] overflow-hidden flex flex-col">
        <FileTree
          files={fileTree}
          selectedFile={selectedFile}
          onFileSelect={setSelectedFile}
        />
      </div>

      {/* Code content */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {currentFile ? (
          <>
            {/* File header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)] bg-[var(--color-bg)]/50">
              <div className="flex items-center gap-2 min-w-0 flex-1">
                <Code2 className="w-4 h-4 text-accent-cyan shrink-0" />
                <span className="font-mono text-sm text-[var(--color-text)] truncate" title={currentFile.path}>
                  {displayPath}
                </span>
              </div>

              <button
                onClick={() => handleCopy(currentFile.content, currentFile.path)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded transition-colors text-[var(--color-muted)] hover:text-accent-cyan hover:bg-accent-cyan/10"
                title="Copy to clipboard"
              >
                {copiedFile === currentFile.path ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-accent-green" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    Copy
                  </>
                )}
              </button>
            </div>

            {/* Code content */}
            <div className="flex-1 overflow-auto p-4 bg-[var(--color-bg)]/30">
              <pre className="font-mono text-sm leading-relaxed">
                <code
                  dangerouslySetInnerHTML={{
                    __html: currentFile.language === 'python' || currentFile.path.endsWith('.py')
                      ? highlightPython(currentFile.content)
                      : currentFile.content,
                  }}
                />
              </pre>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-[var(--color-muted)]">
            <p className="text-sm">Select a file to view its contents</p>
          </div>
        )}
      </div>
    </div>
  );
}
