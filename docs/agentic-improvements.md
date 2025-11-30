# Agentic Improvements - Leveraging Full Potential of Claude Agent SDK

> **Status: IMPLEMENTED** - Most improvements from this document have been implemented.
> For current project state see [ARCHITECTURE.md](./ARCHITECTURE.md).

Historical document describing the transformation of App Builder from a simple chatbot to a robust agentic system leveraging the full power of Claude Code.

## Executive Summary

### Problem

Our App Builder was using Claude Agent SDK as a "dumb wrapper" - sending prompts and waiting for responses without utilizing:
- Native Claude Code tools (Read, Write, Edit, Bash)
- Subagents for specialized tasks
- Hooks for validation and self-correction
- Conversation memory for multi-turn interactions
- Permission callbacks for dynamic control

### Solution

Claude Agent SDK is a **transport layer** to Claude Code CLI. This means we have access to **all Claude Code features** - no need to reimplement them as custom MCP tools.

### Key Changes

| Before | After |
|--------|-------|
| Custom MCP tools for file operations | Native `Read`, `Write`, `Edit`, `Bash` |
| One monolithic agent | Specialized subagents |
| No result validation | Hooks for PostToolUse |
| Stateless (new session each request) | ClaudeSDKClient with memory |
| Hardcoded system prompt | Claude Code preset + append |

---

## Feature Comparison

| Feature | Before | After |
|---------|--------|-------|
| **File Operations** | Custom MCP tools | Native tools ✅ |
| **Code Editing** | Overwrites entire file | `Edit` (surgical changes) ✅ |
| **Shell Commands** | Basic execution | `Bash` with background support ✅ |
| **File Search** | Basic listing | `Glob`, `Grep` with regex ✅ |
| **Subagents** | ❌ None | `agents` parameter ✅ |
| **Hooks** | ❌ None | `PreToolUse`, `PostToolUse` ✅ |
| **Conversation Memory** | ❌ Stateless | `ClaudeSDKClient` ✅ |
| **Permission Control** | ❌ Everything allowed | `can_use_tool` callback ✅ |
| **Error Recovery** | ❌ None | Hooks + subagents ✅ |
| **Cost Tracking** | Basic logging | `ResultMessage.total_cost_usd` ✅ |

---

## Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────────────┐
│                            FRONTEND                                  │
│  Chat Panel + Preview Panel + File Tree                             │
└─────────────────────────────────────────────────────────────────────┘
                                │ WebSocket
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                            BACKEND                                   │
│                                                                      │
│  WebSocket Handler → ClaudeSDKClient (Persistent)                   │
│                                                                      │
│  Options:                                                            │
│  ├── system_prompt: preset + append                                 │
│  ├── allowed_tools: [Read, Write, Edit, Bash, Glob, Grep, Task]    │
│  ├── agents: {code-reviewer, error-fixer}                          │
│  ├── hooks: {PostToolUse: [validate_build]}                        │
│  └── can_use_tool: permission_callback                             │
│                                                                      │
│                      ↓ Spawns subprocess                            │
│                                                                      │
│  Claude Code CLI with native tools                                  │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         SANDBOX LAYER                                │
│  /tmp/sandbox/{session_id}/ - Next.js project files                 │
│  Local (dev) or E2B (production)                                    │
└─────────────────────────────────────────────────────────────────────┘
```

### Self-Correction Flow

```
User Request → Generate Code → Build Project → PostToolUse Hook
                                                      │
                                              Check exit code
                                                      │
                                    ┌─────────────────┴─────────────────┐
                                    │                                   │
                                 SUCCESS                              FAILURE
                                    │                                   │
                                    ▼                                   ▼
                                  Done!                         Code Reviewer Agent
                                                                        │
                                                                        ▼
                                                                Error Fixer Agent
                                                                        │
                                                                        ▼
                                                                 Rebuild (loop)
```

### Multi-Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (Main Agent)                 │
└─────────────────────────────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Code        │ │ Code        │ │ Error       │
│ Generator   │ │ Reviewer    │ │ Fixer       │
│             │ │             │ │             │
│ Model:      │ │ Model:      │ │ Model:      │
│ sonnet      │ │ haiku       │ │ sonnet      │
│             │ │             │ │             │
│ Tools:      │ │ Tools:      │ │ Tools:      │
│ Write,Read  │ │ Read,Grep   │ │ Read,Edit   │
└─────────────┘ └─────────────┘ └─────────────┘
```

---

## Implementation Summary

### Native Tools (replacing custom MCP)

| Old MCP Tool | Native Tool | Benefit |
|--------------|-------------|---------|
| `sandbox_write_file` | `Write` | Standard, tested |
| `sandbox_read_file` | `Read` | Supports images, PDF |
| `sandbox_run_command` | `Bash` | Background, timeout, signals |
| `sandbox_list_files` | `Glob` | Pattern matching |
| - | `Edit` | Surgical changes |
| - | `Grep` | Regex with context |

### Subagents

- **code-reviewer** (Haiku) - Analyzes build errors, cheaper for review tasks
- **error-fixer** (Sonnet) - Applies surgical fixes using Edit tool

### Hooks

- **PreToolUse** - Logging, permission validation
- **PostToolUse** - Build validation, triggers self-correction on failure

### Permission Callback

Blocks dangerous commands (`rm -rf /`, `sudo`, fork bombs) and sensitive file access (`.env`, credentials).

---

## Migration Checklist

All phases completed:

- ✅ Phase 1: Native tools (Read, Write, Edit, Bash, Glob, Grep)
- ✅ Phase 2: Subagents (code-reviewer, error-fixer)
- ✅ Phase 3: Hooks (PostToolUse for build validation)
- ✅ Phase 4: ClaudeSDKClient with conversation memory
- ✅ Phase 5: Permission callbacks
- 🔄 Phase 6: Manual testing in progress

---

## Implementation Reference

See actual implementation in:
- `backend/app/agent.py` - Agent configuration, subagents, hooks
- `backend/app/websocket.py` - WebSocket handler with session management
- `backend/app/local_sandbox_manager.py` - Local sandbox implementation

---

*Document created: 2024-11-28*
*Author: Claude Code analysis*
