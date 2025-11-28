# Lovable for Data Apps

AI-powered builder for data-driven web applications. Think [Lovable](https://lovable.dev) but specialized for dashboards, charts, and data visualization.

## Why Not Vercel AI SDK?

Projects like [e2b-dev/fragments](https://github.com/e2b-dev/fragments) use **Vercel AI SDK** - great for simple code generation, but limited for complex app building:

| Feature | Vercel AI SDK (Fragments) | Claude Agent SDK (This Project) |
|---------|---------------------------|--------------------------------|
| Code generation | ✅ Single-shot | ✅ Multi-turn with memory |
| Error handling | ❌ Manual | ✅ Self-correction loops |
| File operations | ❌ Basic | ✅ Native Read/Write/Edit |
| Subagents | ❌ None | ✅ Specialized (reviewer, fixer) |
| Build validation | ❌ None | ✅ PostToolUse hooks |
| Security | ❌ Basic | ✅ Permission callbacks |

**Claude Agent SDK** gives us full agentic capabilities - the AI can review its own code, fix errors automatically, and delegate to specialized subagents.

## Features

- **Native Claude Code Tools** - Read, Write, Edit, Bash, Glob, Grep
- **Self-Correction** - PostToolUse hooks detect build failures and trigger automatic fixes
- **Specialized Subagents**:
  - `code-reviewer` (Haiku) - Analyzes errors, cheaper for review tasks
  - `error-fixer` (Sonnet) - Surgical code fixes
  - `component-generator` (Sonnet) - React/TypeScript components
- **Conversation Memory** - Multi-turn context across chat messages
- **Permission Control** - Blocks dangerous commands and sensitive file access
- **Live Preview** - Real-time app preview in iframe

## Quick Start

### 1. Setup

```bash
git clone https://github.com/anthropics/e2b-dataapps.git
cd e2b-dataapps

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd frontend && npm install && cd ..
```

### 2. Configure

```bash
cp .env.example .env
# Add your ANTHROPIC_API_KEY
```

### 3. Run

**Terminal 1 - Backend:**
```bash
SANDBOX_MODE=local uvicorn backend.app.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend && npm run dev
```

Open http://localhost:5173

## Architecture

```
┌─────────────────┐     WebSocket      ┌──────────────────────────────────┐
│    Frontend     │◄──────────────────►│           Backend                │
│  React + Vite   │                    │         FastAPI                  │
└─────────────────┘                    │                                  │
                                       │  ┌────────────────────────────┐  │
                                       │  │    AppBuilderAgent         │  │
                                       │  │                            │  │
                                       │  │  • ClaudeSDKClient         │  │
                                       │  │  • Native Tools            │  │
                                       │  │  • Subagents               │  │
                                       │  │  • Hooks                   │  │
                                       │  │  • Permission Callbacks    │  │
                                       │  └────────────────────────────┘  │
                                       │               │                  │
                                       │               ▼                  │
                                       │  ┌────────────────────────────┐  │
                                       │  │   Local Sandbox            │  │
                                       │  │   /tmp/app-builder/{id}/   │  │
                                       │  │                            │  │
                                       │  │   Next.js + TypeScript     │  │
                                       │  │   + Tailwind + shadcn/ui   │  │
                                       │  └────────────────────────────┘  │
                                       └──────────────────────────────────┘
```

## Tech Stack

- **Backend**: FastAPI + Claude Agent SDK
- **Frontend**: React + Vite + Tailwind CSS
- **Sandbox**: Local filesystem (dev) / E2B Cloud (prod)
- **Generated Apps**: Next.js 14 + TypeScript + Tailwind + shadcn/ui

## License

MIT
