import { useState } from 'react';
import { File, Folder, FolderOpen, ChevronRight, ChevronDown } from 'lucide-react';

export interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'folder';
  children?: FileNode[];
}

interface FileTreeProps {
  files: FileNode[];
  selectedFile?: string;
  onFileSelect: (path: string) => void;
}

function getFileIcon(fileName: string) {
  const ext = fileName.split('.').pop()?.toLowerCase();
  switch (ext) {
    case 'py':
      return '🐍';
    case 'js':
    case 'jsx':
    case 'ts':
    case 'tsx':
      return '⚛️';
    case 'json':
      return '📋';
    case 'md':
      return '📝';
    case 'css':
      return '🎨';
    case 'html':
      return '🌐';
    default:
      return null;
  }
}

function FileTreeNode({ node, level = 0, selectedFile, onFileSelect }: {
  node: FileNode;
  level?: number;
  selectedFile?: string;
  onFileSelect: (path: string) => void;
}) {
  const [isOpen, setIsOpen] = useState(true);
  const isFolder = node.type === 'folder';
  const isSelected = node.path === selectedFile;

  const handleClick = () => {
    if (isFolder) {
      setIsOpen(!isOpen);
    } else {
      onFileSelect(node.path);
    }
  };

  return (
    <div>
      <button
        onClick={handleClick}
        className={`w-full flex items-center gap-2 px-2 py-1.5 text-sm transition-colors rounded group ${
          isSelected
            ? 'bg-accent-cyan/20 text-accent-cyan'
            : 'text-[var(--color-text)] hover:bg-[var(--color-bg)]'
        }`}
        style={{ paddingLeft: `${level * 12 + 8}px` }}
      >
        {isFolder && (
          <span className="text-[var(--color-muted)]">
            {isOpen ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
          </span>
        )}
        {!isFolder && <span className="w-3.5" />}

        {isFolder ? (
          isOpen ? (
            <FolderOpen className="w-4 h-4 text-accent-orange shrink-0" />
          ) : (
            <Folder className="w-4 h-4 text-accent-orange shrink-0" />
          )
        ) : (
          <span className="text-base leading-none">{getFileIcon(node.name) || <File className="w-4 h-4 text-[var(--color-muted)]" />}</span>
        )}

        <span className={`truncate font-mono ${isFolder ? 'font-semibold' : ''}`}>
          {node.name}
        </span>
      </button>

      {isFolder && isOpen && node.children && (
        <div>
          {node.children.map((child) => (
            <FileTreeNode
              key={child.path}
              node={child}
              level={level + 1}
              selectedFile={selectedFile}
              onFileSelect={onFileSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function FileTree({ files, selectedFile, onFileSelect }: FileTreeProps) {
  const totalFiles = (nodes: FileNode[]): number => {
    return nodes.reduce((count, node) => {
      if (node.type === 'file') return count + 1;
      return count + (node.children ? totalFiles(node.children) : 0);
    }, 0);
  };

  const fileCount = totalFiles(files);

  if (files.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-[var(--color-muted)] p-4">
        <Folder className="w-8 h-8 mb-2 opacity-30" />
        <p className="text-sm text-center">No files available</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="px-3 py-2 border-b border-[var(--color-border)] bg-[var(--color-bg)]/50">
        <p className="text-xs font-mono text-[var(--color-muted)]">
          {fileCount} {fileCount === 1 ? 'file' : 'files'}
        </p>
      </div>
      <div className="flex-1 overflow-auto p-2">
        {files.map((node) => (
          <FileTreeNode
            key={node.path}
            node={node}
            selectedFile={selectedFile}
            onFileSelect={onFileSelect}
          />
        ))}
      </div>
    </div>
  );
}
