import CodeMirror from '@uiw/react-codemirror';
import { python } from '@codemirror/lang-python';
import { useCallback, useEffect, useState } from 'react';
import { Extension } from '@codemirror/state';
import { EditorView } from '@codemirror/view';

interface CodeEditorProps {
  value: string;
  onChange: (value: string) => void;
}

// Base theme that works for both modes
const baseTheme = {
  '&': {
    backgroundColor: 'transparent',
    height: '100%',
  },
  '.cm-content': {
    caretColor: '#39c5cf',
    fontFamily: '"JetBrains Mono", monospace',
  },
  '.cm-cursor': {
    borderLeftColor: '#39c5cf',
    borderLeftWidth: '2px',
  },
  '&.cm-focused .cm-selectionBackground, .cm-selectionBackground': {
    backgroundColor: 'rgba(57, 197, 207, 0.2) !important',
  },
  '.cm-activeLine': {
    backgroundColor: 'rgba(57, 197, 207, 0.05)',
  },
  '.cm-activeLineGutter': {
    backgroundColor: 'rgba(57, 197, 207, 0.1)',
    color: '#39c5cf',
  },
  '.cm-lineNumbers .cm-gutterElement': {
    padding: '0 12px 0 8px',
    minWidth: '40px',
  },
  '.cm-foldGutter': {
    padding: '0 4px',
  },
};

// Dark mode specific
const darkTheme = {
  ...baseTheme,
  '.cm-gutters': {
    backgroundColor: 'transparent',
    borderRight: '1px solid #1c2128',
    color: '#484f58',
  },
  '.cm-keyword': { color: '#ff7b72' },
  '.cm-string': { color: '#a5d6ff' },
  '.cm-string-2': { color: '#a5d6ff' },
  '.cm-number': { color: '#79c0ff' },
  '.cm-comment': { color: '#8b949e', fontStyle: 'italic' },
  '.cm-variableName': { color: '#ffa657' },
  '.cm-variableName.cm-definition': { color: '#d2a8ff' },
  '.cm-function': { color: '#d2a8ff' },
  '.cm-className': { color: '#f0883e' },
  '.cm-propertyName': { color: '#79c0ff' },
  '.cm-operator': { color: '#ff7b72' },
  '.cm-punctuation': { color: '#c9d1d9' },
  '.cm-bracket': { color: '#c9d1d9' },
  '.cm-tagName': { color: '#7ee787' },
  '.cm-attributeName': { color: '#79c0ff' },
  '.cm-attributeValue': { color: '#a5d6ff' },
  '.cm-meta': { color: '#8b949e' },
  '.cm-atom': { color: '#79c0ff' },
  '.cm-builtin': { color: '#ffa657' },
  '.cm-def': { color: '#d2a8ff' },
};

// Light mode specific
const lightTheme = {
  ...baseTheme,
  '.cm-content': {
    ...baseTheme['.cm-content'],
    caretColor: '#0550ae',
  },
  '.cm-cursor': {
    borderLeftColor: '#0550ae',
    borderLeftWidth: '2px',
  },
  '.cm-gutters': {
    backgroundColor: 'transparent',
    borderRight: '1px solid #e2e8f0',
    color: '#94a3b8',
  },
  '.cm-keyword': { color: '#cf222e' },
  '.cm-string': { color: '#0a3069' },
  '.cm-string-2': { color: '#0a3069' },
  '.cm-number': { color: '#0550ae' },
  '.cm-comment': { color: '#6e7781', fontStyle: 'italic' },
  '.cm-variableName': { color: '#953800' },
  '.cm-variableName.cm-definition': { color: '#8250df' },
  '.cm-function': { color: '#8250df' },
  '.cm-className': { color: '#953800' },
  '.cm-propertyName': { color: '#0550ae' },
  '.cm-operator': { color: '#cf222e' },
  '.cm-punctuation': { color: '#24292f' },
  '.cm-bracket': { color: '#24292f' },
  '.cm-tagName': { color: '#116329' },
  '.cm-attributeName': { color: '#0550ae' },
  '.cm-attributeValue': { color: '#0a3069' },
  '.cm-meta': { color: '#6e7781' },
  '.cm-atom': { color: '#0550ae' },
  '.cm-builtin': { color: '#953800' },
  '.cm-def': { color: '#8250df' },
};

export default function CodeEditor({ value, onChange }: CodeEditorProps) {
  const [isDark, setIsDark] = useState(document.documentElement.classList.contains('dark'));

  // Listen for theme changes
  useEffect(() => {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.attributeName === 'class') {
          setIsDark(document.documentElement.classList.contains('dark'));
        }
      });
    });

    observer.observe(document.documentElement, { attributes: true });
    return () => observer.disconnect();
  }, []);

  const handleChange = useCallback(
    (val: string) => {
      onChange(val);
    },
    [onChange]
  );

  const customTheme: Extension = EditorView.theme(isDark ? darkTheme : lightTheme);

  return (
    <CodeMirror
      key={isDark ? 'dark' : 'light'} // Force re-render on theme change
      value={value}
      height="100%"
      extensions={[python(), customTheme]}
      onChange={handleChange}
      basicSetup={{
        lineNumbers: true,
        highlightActiveLineGutter: true,
        highlightActiveLine: true,
        foldGutter: true,
        dropCursor: true,
        allowMultipleSelections: true,
        indentOnInput: true,
        bracketMatching: true,
        closeBrackets: true,
        autocompletion: true,
        rectangularSelection: true,
        crosshairCursor: false,
        highlightSelectionMatches: true,
      }}
      className="h-full text-sm"
    />
  );
}
