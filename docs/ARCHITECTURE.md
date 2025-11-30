# E2B Data Apps Builder - Architecture

> AI-powered application builder using Claude Agent SDK with real-time preview

## Overview

This project is a full-stack application that enables users to build web applications through natural language conversation with Claude. The AI agent writes code, runs commands, and provides live preview of the generated application.

## Key Features

- **Conversational app building** - Describe what you want, Claude builds it
- **Real-time code streaming** - See code as it's being written
- **Live preview** - Instant preview of the running application
- **Self-correction** - Automatic error detection and fixing via subagents
- **Dual sandbox modes** - Local development or E2B cloud sandboxes
- **Session persistence** - Conversation memory within session

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
│  ┌─────────────────┐     ┌─────────────────────────────┐   │
│  │   Chat Panel    │     │     Preview Panel           │   │
│  │  - Messages     │     │  - Live iframe              │   │
│  │  - Tool use     │     │  - Code viewer              │   │
│  │  - Input        │     │  - Console logs             │   │
│  └────────┬────────┘     └──────────────┬──────────────┘   │
└───────────┼─────────────────────────────┼──────────────────┘
            │ WebSocket                    │
            ▼                              │
┌─────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI)                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              ConnectionManager                       │   │
│  │   - WebSocket connections                           │   │
│  │   - Agent lifecycle                                 │   │
│  │   - Message routing                                 │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         │                                   │
│  ┌──────────────────────▼──────────────────────────────┐   │
│  │              AppBuilderAgent                         │   │
│  │   - ClaudeSDKClient wrapper                         │   │
│  │   - Subagents (code-reviewer, error-fixer)          │   │
│  │   - PostToolUse hooks for self-correction           │   │
│  │   - Permission callbacks                            │   │
│  └──────────────────────┬──────────────────────────────┘   │
│                         │                                   │
│  ┌──────────────────────▼──────────────────────────────┐   │
│  │        SandboxManager (Local or E2B)                 │   │
│  │   - File operations                                 │   │
│  │   - Command execution                               │   │
│  │   - Dev server management                           │   │
│  │   - Preview URL generation                          │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

### Frontend
| Technology | Purpose |
|------------|---------|
| React 18 | UI framework |
| Zustand | State management |
| CodeMirror 6 | Code editor |
| Tailwind CSS | Styling |
| Framer Motion | Animations |
| React Markdown | Message rendering |
| Vite | Build tool |

### Backend
| Technology | Purpose |
|------------|---------|
| FastAPI | Web framework |
| Claude Agent SDK | AI agent integration |
| E2B SDK | Cloud sandbox (optional) |
| WebSockets | Real-time communication |
| Uvicorn | ASGI server |

## Directory Structure

```
e2b-dataapps/
├── backend/
│   └── app/
│       ├── main.py                 # FastAPI entry point
│       ├── websocket.py            # ConnectionManager
│       ├── agent.py                # AppBuilderAgent + subagents + hooks
│       ├── sandbox_manager.py      # E2B cloud sandbox
│       ├── local_sandbox_manager.py # Local filesystem sandbox
│       ├── logging_config.py       # Session-scoped logging
│       └── tools/
│           └── sandbox_tools.py    # MCP tools
├── frontend/
│   └── src/
│       ├── AppBuilder.tsx          # Main app builder UI
│       ├── App.tsx                 # Streamlit launcher (legacy)
│       ├── lib/
│       │   ├── store.ts            # Zustand store
│       │   └── websocket.ts        # WebSocket client
│       └── components/
│           ├── chat/               # Chat UI components
│           └── preview/            # Preview panel components
├── docs/
│   ├── ARCHITECTURE.md             # This file
│   └── agentic-improvements.md     # Implementation history
└── tests/                          # Test files
```

## Sandbox Modes

### Local Mode (`SANDBOX_MODE=local`)
- Uses local filesystem at `/tmp/app-builder/{session_id}`
- **Native Claude Code tools**: Read, Write, Edit, Bash, Glob, Grep
- Dev server runs locally on allocated port (3001+)
- Faster for development, no cloud dependency

### E2B Mode (`SANDBOX_MODE=e2b`)
- Uses E2B cloud sandboxes with `keboola-apps-builder` template
- All operations via MCP tools
- Isolated cloud environment
- Requires E2B API key

## Agent Architecture

### Main Agent
The `AppBuilderAgent` wraps `ClaudeSDKClient` and provides:
- System prompt with app building context
- Tool access (native or MCP-based)
- Subagent definitions
- Hook configurations
- Permission callbacks

### Subagents
Specialized agents for specific tasks:

| Agent | Model | Purpose | Tools |
|-------|-------|---------|-------|
| `code-reviewer` | Haiku | Analyze errors, find issues | Read, Grep, Glob |
| `error-fixer` | Sonnet | Apply surgical fixes | Read, Edit |
| `component-generator` | Sonnet | Generate React components | Write, Read |

### Self-Correction Hooks

**PostToolUse Hook** monitors build commands:
```
Build fails → Hook injects system message →
Agent uses code-reviewer → Agent uses error-fixer →
Agent rebuilds → Repeat until success
```

### Permission Callbacks
Dynamic tool access control:
- Blocks dangerous commands (`rm -rf /`, `sudo`, fork bombs)
- Blocks sensitive file access (`.env`, `.ssh/`, credentials)
- Logs suspicious patterns

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/api/session` | POST | Create new session |
| `/api/sessions` | GET | List active sessions |
| `/ws/chat/{session_id}` | WS | Real-time chat |

## WebSocket Events

### Client → Server
```json
{"type": "chat", "message": "user input"}
{"type": "ping"}
{"type": "reset"}
```

### Server → Client
```json
{"type": "connection", "session_id": "..."}
{"type": "text", "content": "streaming text"}
{"type": "tool_use", "tool": "Write", "input": {...}}
{"type": "tool_result", "result": {...}}
{"type": "done", "preview_url": "http://localhost:3001"}
```

## Running the Project

### Prerequisites
- Python 3.11+
- Node.js 18+
- Claude API key

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
SANDBOX_MODE=local uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Environment Variables
```bash
# Backend (.env)
ANTHROPIC_API_KEY=sk-...
SANDBOX_MODE=local  # or "e2b"
E2B_API_KEY=...     # if using E2B mode

# Optional
CLAUDE_MODEL=claude-sonnet-4-5
```

## Session Logging

Each session creates logs in `logs/{session_id}/`:
- `session.log` - Main timeline
- `websocket.log` - All WebSocket traffic
- `agent.log` - Agent events
- `sandbox.log` - Sandbox operations
- `errors.log` - Errors with tracebacks
- `llm_requests.jsonl` - Claude API requests
- `llm_responses.jsonl` - Claude API responses
- `tool_calls.jsonl` - Tool execution logs

## Security Measures

1. **Path traversal protection** - All paths validated within sandbox
2. **Command filtering** - Dangerous shell commands blocked
3. **Sensitive file blocking** - Credentials and secrets protected
4. **Sandbox isolation** - Local or cloud container isolation
5. **Tool logging** - Complete audit trail

## Performance

- **Streaming responses** - Real-time text updates
- **Lazy sandbox init** - Created only when needed
- **Port allocation** - Dynamic port scanning
- **Async I/O** - Non-blocking file and network operations
- **Connection pooling** - Efficient WebSocket management

## Known Limitations

1. Local mode doesn't support multiple simultaneous sessions on same port range
2. E2B mode has 30-minute timeout
3. Large files may be truncated in logs
4. No persistent session storage (memory only)
