# E2B Data Apps Builder

AI-powered application builder using Claude Agent SDK. Users describe apps in natural language, Claude builds them with live preview.

## Project Structure

```
backend/app/          # FastAPI + Claude Agent SDK
frontend/src/         # React + Zustand + WebSocket
components/curated/   # Pre-built UI components for generated apps
scripts/              # Utility scripts (Keboola testing, etc.)
docs/                 # Architecture documentation
tests/                # Test files
e2b-integration/      # E2B sandbox templates (parked)
```

## Key Files

- `backend/app/agent.py` - Main agent with subagents and hooks
- `backend/app/websocket.py` - WebSocket connection manager
- `backend/app/local_sandbox_manager.py` - Local sandbox (primary mode)
- `frontend/src/AppBuilder.tsx` - Main UI component
- `frontend/src/lib/store.ts` - Zustand state
- `frontend/src/lib/websocket.ts` - WebSocket client

## Running Locally

```bash
# Backend
cd backend && source .venv/bin/activate
SANDBOX_MODE=local uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev
```

## Architecture Principles

### Agent Design
- **Native tools over MCP** - Use Read, Write, Edit, Bash, Glob, Grep directly
- **Subagents for specialization** - code-reviewer (Haiku), error-fixer (Sonnet)
- **Self-correction via hooks** - PostToolUse hook triggers fixes on build failure
- **Permission callbacks** - Block dangerous commands and sensitive files

### Sandbox Modes
- `SANDBOX_MODE=local` - Local filesystem at `/tmp/app-builder/{session_id}`
- `SANDBOX_MODE=e2b` - E2B cloud sandbox (requires API key)

### WebSocket Protocol
Client sends: `{"type": "chat|ping|reset", "message": "..."}`
Server streams: `text`, `tool_use`, `tool_result`, `done`

## Testing

```bash
cd backend
pytest tests/ -v
```

## Common Tasks

### Adding a new subagent
Edit `backend/app/agent.py` - add to `AGENTS` dict with:
- `description` - When to use
- `prompt` - Instructions
- `tools` - Allowed tools
- `model` - haiku/sonnet

### Adding a new hook
Edit `backend/app/agent.py` - add to `HOOKS` dict:
- `PreToolUse` - Before tool execution
- `PostToolUse` - After tool execution (for validation)

### Modifying sandbox behavior
- Local: `backend/app/local_sandbox_manager.py`
- E2B: `backend/app/sandbox_manager.py`
