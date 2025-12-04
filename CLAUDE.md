# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered app builder using Claude Agent SDK. Users describe apps in natural language, Claude builds them with live preview via WebSocket streaming.

## Commands

```bash
# Backend (use python3.13 venv)
cd backend && source .venv/bin/activate
SANDBOX_MODE=local uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# Tests
cd backend && pytest tests/ -v
pytest tests/test_permission_callback.py -v  # single test file
pytest tests/test_api.py::test_health -v     # single test
```

## Architecture

**Backend (FastAPI + Claude Agent SDK):**
- `agent.py` - AppBuilderAgent with subagents (code-reviewer, error-fixer), hooks (PostToolUse for self-correction), and permission callbacks
- `websocket.py` - ConnectionManager for WebSocket lifecycle
- `local_sandbox_manager.py` - Local sandbox at `/tmp/app-builder/{session_id}`
- `sandbox_manager.py` - E2B cloud sandbox (alternative mode)

**Frontend (React + Zustand):**
- `AppBuilder.tsx` - Main UI with chat and preview panels
- `lib/store.ts` - Zustand state management
- `lib/websocket.ts` - WebSocket client with reconnection

## Agent Design Patterns

- **Native tools over MCP** - Read, Write, Edit, Bash, Glob, Grep directly (in local mode)
- **Subagents** - code-reviewer (Haiku, cheap), error-fixer (Sonnet)
- **Self-correction** - PostToolUse hook on Bash detects build failures, injects system message to trigger fix loop
- **Permission callbacks** - Block `rm -rf /`, `sudo`, `.env` access, etc.

## WebSocket Protocol

```
Client → Server: {"type": "chat|ping|reset", "message": "..."}
Server → Client: text, tool_use, tool_result, done (with preview_url)
```

## Modifying Agent Behavior

**Add subagent** - Edit `agent.py`, add to `AGENTS` dict with description, prompt, tools, model

**Add hook** - Edit `agent.py`, add to `HOOKS` dict (PreToolUse or PostToolUse)

## Keboola Integration

### Critical Rules
- **Always use JSON format** - CSV parsing fails with HTML/special chars
- **Max 1000 rows per request** - Undocumented limit, fails silently
- Use `format=json` and `cache: 'no-store'` in fetch

### API Endpoints
```bash
# List buckets
curl -H "X-StorageApi-Token: $KBC_TOKEN" "$KBC_URL/v2/storage/buckets"

# Preview table (ALWAYS use format=json)
curl -H "X-StorageApi-Token: $KBC_TOKEN" \
  "$KBC_URL/v2/storage/tables/{table_id}/data-preview?limit=1000&format=json"
```

### Common Gotchas
| Problem | Cause | Solution |
|---------|-------|----------|
| Empty rows | limit > 1000 | Use max 1000 |
| CSV parse fails | HTML in data | Use format=json |
| Stale data | Next.js cache | Use cache: 'no-store' |

## Context7 Usage

When standard approach fails twice, fetch live docs:

```
# Step 1: Find library ID
mcp__context7__resolve-library-id with libraryName: "nextjs"

# Step 2: Get specific docs
mcp__context7__get-library-docs with libraryId: "/vercel/next.js", topic: "environment variables"
```

### Query Examples
| Situation | libraryName | topic |
|-----------|-------------|-------|
| Env vars not loading | nextjs | environment variables app router |
| API route issues | nextjs | route handlers app router |
| Chart not rendering | recharts | ResponsiveContainer |

## Debugging Workflow

1. **Test in isolation** - curl the API directly before changing code
2. **Read full error** - Don't guess, understand root cause
3. **Use Context7** - If standard approach fails twice, fetch docs
4. **Check logs** - `cat /tmp/nextjs.log` for server errors
