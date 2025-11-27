# E2B Streamlit Launcher - Frontend

Modern web interface for launching Streamlit apps in E2B sandboxes.

## Features

- **Code Editor** - Python syntax highlighting with CodeMirror
- **Real-time Logs** - SSE streaming of sandbox events
- **Live Preview** - Embedded iframe with running Streamlit app
- **Template Selection** - Choose pre-built templates for faster startup
- **Example Scripts** - Quick-start examples built-in

## Quick Start

```bash
# Install dependencies
npm install

# Start development server (requires backend running on :8000)
npm run dev
```

Open http://localhost:3000

## Tech Stack

- React 18 + TypeScript
- Vite
- Tailwind CSS
- CodeMirror 6
- Framer Motion
- Lucide Icons

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── CodeEditor.tsx      # Python code editor
│   │   ├── LogTerminal.tsx     # Real-time log viewer
│   │   ├── SandboxPreview.tsx  # Iframe preview
│   │   ├── TemplateSelector.tsx
│   │   └── ExampleSelector.tsx
│   ├── types/
│   │   └── index.ts            # TypeScript types
│   ├── App.tsx                 # Main application
│   ├── main.tsx                # Entry point
│   └── index.css               # Global styles
├── public/
│   └── e2b-icon.svg
└── index.html
```

## Design

Terminal-inspired dark theme with:
- JetBrains Mono for code
- Space Grotesk for UI
- Cyan/Green accent colors
- Subtle animations and glowing effects
