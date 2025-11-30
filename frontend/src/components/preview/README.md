# Preview Components

A set of React components for displaying app previews, code files, and console output in the App Builder frontend.

## Components

### PreviewPanel (Main Component)

The main container component that provides a tabbed interface for Preview, Code, and Console views.

```tsx
import { PreviewPanel } from './components/preview';

function App() {
  const [previewUrl, setPreviewUrl] = useState<string>();
  const [consoleLogs, setConsoleLogs] = useState<ConsoleLog[]>([]);
  const [codeFiles, setCodeFiles] = useState<CodeFile[]>([]);

  return (
    <PreviewPanel
      previewUrl={previewUrl}
      codeFiles={codeFiles}
      consoleLogs={consoleLogs}
      onClearConsole={() => setConsoleLogs([])}
    />
  );
}
```

**Props:**
- `previewUrl?: string` - URL to display in iframe
- `codeFiles?: CodeFile[]` - Array of code files to display
- `consoleLogs?: ConsoleLog[]` - Array of console log entries
- `onClearConsole?: () => void` - Callback when clear button is clicked

---

### PreviewIframe

Iframe wrapper with loading states and error handling.

```tsx
import { PreviewIframe } from './components/preview';

<PreviewIframe
  url="https://example.com"
  refreshKey={refreshCounter} // Change to force refresh
/>
```

**Props:**
- `url: string` - URL to load in iframe
- `refreshKey?: number` - Key to force iframe refresh (increment to reload)

---

### CodeView

Code file viewer with file tree navigation and syntax highlighting.

```tsx
import { CodeView, CodeFile } from './components/preview';

const files: CodeFile[] = [
  {
    path: 'src/app.py',
    content: 'import streamlit as st\n\nst.title("Hello")',
    language: 'python'
  },
  {
    path: 'src/utils.py',
    content: 'def helper(): pass',
    language: 'python'
  }
];

<CodeView files={files} />
```

**Props:**
- `files: CodeFile[]` - Array of code files to display

**CodeFile Interface:**
```ts
interface CodeFile {
  path: string;        // File path (e.g., 'src/app.py')
  content: string;     // File contents
  language?: string;   // Language for syntax highlighting
}
```

---

### ConsoleOutput

Console/terminal output viewer with timestamps and log levels.

```tsx
import { ConsoleOutput, ConsoleLog } from './components/preview';

const logs: ConsoleLog[] = [
  {
    id: '1',
    timestamp: Date.now(),
    message: 'Server started',
    type: 'info'
  },
  {
    id: '2',
    timestamp: Date.now(),
    message: 'Request received',
    type: 'stdout'
  },
  {
    id: '3',
    timestamp: Date.now(),
    message: 'Error occurred',
    type: 'stderr'
  }
];

<ConsoleOutput
  logs={logs}
  onClear={() => setLogs([])}
/>
```

**Props:**
- `logs: ConsoleLog[]` - Array of log entries
- `onClear?: () => void` - Callback when clear button is clicked

**ConsoleLog Interface:**
```ts
interface ConsoleLog {
  id: string;          // Unique identifier
  timestamp: number;   // Unix timestamp
  message: string;     // Log message
  type: 'stdout' | 'stderr' | 'info';  // Log type
}
```

---

### FileTree

File tree navigation component (used internally by CodeView).

```tsx
import { FileTree, FileNode } from './components/preview';

const files: FileNode[] = [
  {
    name: 'src',
    path: 'src',
    type: 'folder',
    children: [
      { name: 'app.py', path: 'src/app.py', type: 'file' }
    ]
  }
];

<FileTree
  files={files}
  selectedFile="src/app.py"
  onFileSelect={(path) => console.log(path)}
/>
```

**Props:**
- `files: FileNode[]` - Array of file/folder nodes
- `selectedFile?: string` - Currently selected file path
- `onFileSelect: (path: string) => void` - Callback when file is selected

**FileNode Interface:**
```ts
interface FileNode {
  name: string;        // File/folder name
  path: string;        // Full path
  type: 'file' | 'folder';
  children?: FileNode[];  // Child nodes (for folders)
}
```

## Styling

All components use:
- Tailwind CSS with CSS variables from the theme
- Lucide icons
- Framer Motion for animations
- Responsive design patterns from existing components

## Features

- **PreviewPanel**: Tab switching, refresh button, open in new tab
- **PreviewIframe**: Loading skeleton, error state, sandboxed iframe
- **CodeView**: File tree, syntax highlighting (Python), copy to clipboard
- **ConsoleOutput**: Auto-scroll, timestamps, color-coded logs, clear button
- **FileTree**: Collapsible folders, file icons, selection state
