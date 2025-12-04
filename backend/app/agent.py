#!/usr/bin/env python3
"""
AppBuilderAgent - Claude Agent SDK wrapper for Next.js/React/TypeScript app builder.

AGENTIC IMPROVEMENTS IMPLEMENTATION:
- Phase 2: Native Claude Code tools (Read, Write, Edit, Bash, Glob, Grep)
- Phase 3: Specialized subagents (code-reviewer, error-fixer, component-generator)
- Phase 4: Hooks for self-correction (PostToolUse) and logging (PreToolUse)
- Phase 5: ClaudeSDKClient with conversation memory
- Phase 6: Permission callbacks for security (can_use_tool)

Features:
- Native tools for file operations (Read, Write, Edit) in LOCAL mode
- Native Bash for command execution with timeout support
- Native Glob/Grep for file search
- System prompt using preset + append pattern
- MCP server only for E2B-specific tools (preview URL, dev server)
- Subagents: code-reviewer (haiku), error-fixer (sonnet), component-generator (sonnet)
- Self-correction hooks when build fails
- Permission callback blocking dangerous commands and sensitive file access
- Conversation memory across multiple chat turns
"""

import logging
import os
import re
import tempfile
import time
from pathlib import Path
from typing import AsyncIterator, Callable, Optional

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    HookMatcher,
    AgentDefinition,
)

from .sandbox_factory import create_sandbox_manager
from .tools.sandbox_tools import create_sandbox_tools_server, create_e2b_only_server
from .logging_config import get_session_logger

# Default model if not specified in environment
DEFAULT_MODEL = "claude-sonnet-4-5"


def get_sandbox_mode() -> str:
    """Get the current sandbox mode from environment."""
    return os.getenv("SANDBOX_MODE", "local").lower()


# =============================================================================
# SYSTEM PROMPT - Using preset + append pattern
# =============================================================================

SYSTEM_PROMPT_APPEND = """
## App Builder Context

You are building data-driven web applications in a sandbox environment.
The sandbox has Next.js 14 with TypeScript, Tailwind CSS, and shadcn/ui pre-configured.

### Context Window Conservation (CRITICAL)
- Be concise - no unnecessary explanations or narration
- Limit data samples to 5 rows max
- Use `jq` to filter API responses - never dump raw JSON
- Don't repeat information already discussed
- Use targeted Grep patterns instead of reading entire files

### Your Capabilities

**Native Tools (prefer these for file operations):**
- `Read` - Read file contents (use offset/limit for large files)
- `Write` - Create or overwrite files
- `Edit` - Surgical changes (old_string → new_string) - PREFER over Write
- `Bash` - Shell commands with timeout support
- `Glob` - Find files by pattern
- `Grep` - Search file contents with regex

**Sandbox Tools:**
- `mcp__e2b__sandbox_start_dev_server` - Start Next.js dev server (ALWAYS use this, never npm run dev via Bash!)
- `mcp__e2b__sandbox_get_preview_url` - Get live preview URL

**Documentation Tools (use when stuck):**
- `mcp__context7__resolve-library-id` - Find library ID
- `mcp__context7__get-library-docs` - Get documentation for specific topic

### Workflow

0. **Discover** (for data apps) - Before building:
   - Use `data-explorer` subagent to find available Keboola tables
   - Ask user which data to visualize (max 2-3 clarifying questions)
   - Confirm understanding: "I'll build X showing Y data with Z features. OK?"
   - Only proceed after user confirms

1. **Create** - Use `Write` to create new files
2. **Edit** - Use `Edit` for modifications (NOT Write for existing files)
3. **Verify** - Run `npm run build` via Bash to check for errors
4. **Fix** - If errors, use `code-reviewer` then `error-fixer` subagents
5. **Preview** - Start dev server and provide preview URL

### Code Quality

- Always use TypeScript with proper types
- Use 'use client' for interactive components
- Follow React best practices (hooks, composition)
- Make UI responsive with Tailwind CSS
- Handle loading and error states

### CRITICAL: next.config.js for Preview

ALWAYS create this next.config.js to allow iframe preview:

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-Frame-Options', value: 'ALLOWALL' },
          { key: 'Content-Security-Policy', value: "frame-ancestors 'self' http://localhost:* http://127.0.0.1:*" },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
```

### Project Structure

```
/app
  /layout.tsx          # Root layout
  /page.tsx            # Home page
  /api/                # API routes
/components
  /ui/                 # shadcn/ui components
  /charts/             # Chart components
/lib
  /utils.ts            # Utility functions
  /keboola.ts          # Keboola API utilities
/types
  /index.ts            # TypeScript types
```

### Running & Validation

Before considering the app complete:
1. Run `npm install` via Bash
2. Run `npm run build` via Bash to verify no errors
3. Use `mcp__e2b__sandbox_start_dev_server` to start the dev server
4. The tool returns the preview URL - share it with the user

### CRITICAL: Dev Server Rules

**NEVER run `npm run dev` via Bash!** It will use port 3000 which conflicts with the frontend.
**ALWAYS use `mcp__e2b__sandbox_start_dev_server` tool** - it automatically allocates a free port (3001+) and returns the correct preview URL.

### Subagents Available

Delegate to specialized subagents via Task tool:
- `data-explorer`: Discovers Keboola tables/schemas. Use FIRST for data apps.
- `code-reviewer`: Analyzes build errors. Use when build fails.
- `error-fixer`: Applies surgical code fixes.
- `component-generator`: Creates React components.

---

## Keboola Storage API Reference

When working with Keboola data, use these patterns:

### Authentication
- Token is available as `$KBC_TOKEN` environment variable
- Always use header: `X-StorageApi-Token: $KBC_TOKEN`

### CRITICAL: Use JSON Format, Not CSV
CSV parsing fails with complex data (HTML, nested quotes). **Always use JSON format:**
```bash
curl -s -H "X-StorageApi-Token: $KBC_TOKEN" \\
  "${KBC_URL}/v2/storage/tables/{table_id}/data-preview?limit=1000&format=json"
```

### API Limits
- **Maximum limit per request: 1000 rows** (not documented, fails silently with higher values!)
- For larger datasets, use pagination with `offset` parameter
- For very large datasets (>100k rows), use async export or pre-aggregate in Keboola

### Response Structure (JSON format)
```json
{
  "columns": ["col1", "col2"],
  "rows": [
    {"col1": "value1", "col2": "value2"}
  ]
}
```

### Common Endpoints
```bash
# List buckets
curl -s -H "X-StorageApi-Token: $KBC_TOKEN" "${KBC_URL}/v2/storage/buckets"

# List tables in bucket
curl -s -H "X-StorageApi-Token: $KBC_TOKEN" "${KBC_URL}/v2/storage/buckets/{bucket_id}/tables"

# Preview table data (ALWAYS use format=json!)
curl -s -H "X-StorageApi-Token: $KBC_TOKEN" \\
  "${KBC_URL}/v2/storage/tables/{table_id}/data-preview?limit=1000&format=json"
```

### Recommended Keboola Utility (create in /lib/keboola.ts)
```typescript
const KBC_URL = process.env.KBC_URL || 'https://connection.north-europe.azure.keboola.com';

export async function fetchTable(tableId: string, limit = 1000) {
  const token = process.env.KBC_TOKEN;
  const response = await fetch(
    `${KBC_URL}/v2/storage/tables/${tableId}/data-preview?limit=${limit}&format=json`,
    {
      headers: { 'X-StorageApi-Token': token || '' },
      cache: 'no-store'
    }
  );
  if (!response.ok) throw new Error(`Keboola API error: ${response.status}`);
  const data = await response.json();
  return data.rows || [];
}

export async function fetchTablePaginated(tableId: string, maxRows = 5000) {
  const allRows = [];
  let offset = 0;
  const limit = 1000;

  while (allRows.length < maxRows) {
    const response = await fetch(
      `${KBC_URL}/v2/storage/tables/${tableId}/data-preview?limit=${limit}&offset=${offset}&format=json`,
      { headers: { 'X-StorageApi-Token': process.env.KBC_TOKEN || '' }, cache: 'no-store' }
    );
    const { rows } = await response.json();
    if (!rows || rows.length === 0) break;
    allRows.push(...rows);
    offset += limit;
  }
  return allRows;
}
```

### Common Gotchas
| Problem | Cause | Solution |
|---------|-------|----------|
| Empty `rows` array | limit > 1000 | Use limit=1000 max |
| CSV parsing fails | HTML/special chars in data | Use format=json |
| 401 Unauthorized | Bad token | Check $KBC_TOKEN |
| Stale data | Next.js caching | Use cache: 'no-store' |

---

## Debugging Workflow

When something doesn't work, follow this systematic approach:

### 1. Test in Isolation First (before changing code)
```bash
# Test Keboola API directly
curl -s -H "X-StorageApi-Token: $KBC_TOKEN" \\
  "${KBC_URL}/v2/storage/tables/{table_id}/data-preview?limit=5&format=json"

# Test if command works
node -e "console.log(process.env.KBC_TOKEN ? 'Token set' : 'No token')"
```

### 2. If Standard Approach Fails Twice, Use Context7
Don't keep guessing. Fetch actual documentation:
```
# Step 1: Find library ID
mcp__context7__resolve-library-id with libraryName: "nextjs"

# Step 2: Get specific docs
mcp__context7__get-library-docs with libraryId: "/vercel/next.js" and topic: "environment variables app router"
```

### Context7 Query Examples by Situation
| Situation | libraryName | topic |
|-----------|-------------|-------|
| Env vars not loading | nextjs | environment variables app router |
| API route issues | nextjs | route handlers app router |
| Fetch caching | nextjs | fetch cache revalidate |
| Chart not rendering | recharts | ResponsiveContainer |
| Tailwind not applying | tailwindcss | configuration content |

### 3. Check Server Logs
```bash
cat /tmp/nextjs.log  # or wherever dev server logs
```

### 4. Don't Guess - Understand Root Cause
If something fails:
1. Read the FULL error message
2. Test the minimal case in isolation
3. Look up docs if behavior is unexpected
4. Fix with understanding, not trial-and-error

---

## Error Handling Patterns

### Build Errors
1. Read the error message carefully
2. Use Glob/Grep to find the problematic files
3. Use Read to examine the context
4. Use Edit to fix the issues surgically
5. Run build again to verify

### API/Data Errors
1. Test API call directly with curl
2. Check response format (is it what you expect?)
3. Verify authentication (is token set?)
4. Check limits and pagination

### Runtime Errors
1. Check browser console (mention this to user if needed)
2. Check server logs
3. Add console.log for debugging
4. Remove debug code after fixing
"""

# =============================================================================
# SUBAGENTS - Specialized agents for different tasks
# =============================================================================

# Context conservation note - applies to all agents
CONTEXT_CONSERVATION_NOTE = """
## Context Window Conservation (CRITICAL)
- Be concise in responses - no unnecessary explanations
- Limit data samples to 5 rows max
- Truncate long outputs (show first/last 10 lines of large files)
- Don't repeat information already in context
- Use targeted Grep patterns instead of reading entire files
- Report only essential findings, not process narration
"""

AGENTS = {
    "data-explorer": AgentDefinition(
        description="Explores Keboola project to discover available data sources. Use BEFORE building data apps to understand what data exists.",
        prompt=f"""You are a data discovery specialist.

## FIRST: Check Credentials
Run this check before anything else:
```bash
if [ -z "$KBC_TOKEN" ] || [ -z "$KBC_URL" ]; then
  echo "ERROR: Keboola credentials not configured. Cannot explore data."
  echo "Set KBC_TOKEN and KBC_URL environment variables."
  exit 0
fi
echo "Credentials OK: $KBC_URL"
```

## Process
1. List buckets (filter system buckets, max 10):
   `curl -s -H "X-StorageApi-Token: $KBC_TOKEN" "$KBC_URL/v2/storage/buckets" | jq '[.[] | select(.id | (startswith("in.") or startswith("out.c-")) and (contains("sys.") | not) and (contains("out.c-_") | not)) | {{id, name}}] | .[0:10]'`
2. For relevant buckets (max 3), list tables with row counts
3. For key tables (max 3), get column names and sample 3-5 rows

## Output Format (compact)
```
## Data Sources (credentials: OK)

### Bucket: in.c-sales (2 tables)
- orders: 15,234 rows | id, customer_id, amount, date
- customers: 1,203 rows | id, name, email, segment

### Sample: in.c-sales.orders (3 of 15,234 rows)
| id | customer_id | amount | date |
| 1 | 42 | 150.00 | 2024-01-15 |
```

## Rules
- Check credentials FIRST - exit gracefully if missing
- Filter: `in.*` and `out.c-*` only, exclude `sys.*` and `out.c-_*`
- Cap: 10 buckets, 3 table samples, 5 rows per sample
- Use `format=json` and `limit=5` for data samples
- Use `jq` to filter JSON output - never dump raw responses
{CONTEXT_CONSERVATION_NOTE}""",
        tools=["Bash"],
        model="haiku"  # Cheap for exploration
    ),

    "code-reviewer": AgentDefinition(
        description="Reviews TypeScript/React code for errors. Use when build fails or you need code review.",
        prompt=f"""You are an expert TypeScript/React code reviewer.

## Your Task
Analyze error messages and source code to identify issues.

## Process
1. Read the error message carefully
2. Use Grep to find the problematic code (targeted patterns only)
3. Use Read to examine minimal context around the issue
4. Identify the exact issue

## Output Format (compact)
```
FILE: path/to/file.tsx:42
ISSUE: Missing import for useState
FIX: Add `import {{ useState }} from 'react'`
```

## Rules
- Only report issues with confidence >= 80%
- Focus on actual errors, not style preferences
- Be specific about line numbers and fixes
- Don't read entire files - use Grep to find specific lines
{CONTEXT_CONSERVATION_NOTE}""",
        tools=["Read", "Grep", "Glob"],
        model="haiku"  # Cost-effective for review tasks
    ),

    "error-fixer": AgentDefinition(
        description="Fixes specific code errors identified by code-reviewer.",
        prompt=f"""You are a precise code fixer.

## Your Task
Apply specific fixes to code based on error analysis.

## Process
1. Read only the relevant section of the file (use offset/limit if large)
2. Use Edit to make surgical changes (old_string → new_string)
3. Briefly confirm what you changed (one line)

## Rules
- Use Edit tool, NOT Write (preserves more context)
- Make minimal changes - fix only what's broken
- One fix at a time
- Don't explain the fix in detail - just state what changed
{CONTEXT_CONSERVATION_NOTE}""",
        tools=["Read", "Edit"],
        model="sonnet"
    ),

    "component-generator": AgentDefinition(
        description="Generates React components with TypeScript and Tailwind. Use for creating new UI components.",
        prompt=f"""You are a React component specialist.

## Stack
- React 18 with hooks
- TypeScript strict mode
- Tailwind CSS for styling
- shadcn/ui for UI primitives

## Component Template
```typescript
'use client'  // Only if using hooks/state/effects

interface Props {{
  // Define props with types
}}

export default function ComponentName({{ prop1 }}: Props) {{
  return <div className="...">...</div>
}}
```

## Rules
- Use 'use client' ONLY for components with state/effects/events
- Include TypeScript types for all props
- Make responsive with Tailwind (mobile-first)
- Include loading and error states where appropriate
- Don't add unnecessary comments or documentation
{CONTEXT_CONSERVATION_NOTE}""",
        tools=["Write", "Read"],
        model="sonnet"
    ),
}


# =============================================================================
# HOOKS - Self-correction and logging
# =============================================================================

async def validate_build_result(
    input_data: dict,
    tool_use_id: str | None,
    context: dict
) -> dict:
    """
    PostToolUse hook - validates build results and triggers self-correction.

    When `npm run build` or `npx tsc` fails, this hook adds a system message
    instructing the agent to use subagents to analyze and fix the errors.
    """
    if input_data.get("tool_name") != "Bash":
        return {}

    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")
    response = input_data.get("tool_response", {})

    # Get exit code from response
    exit_code = response.get("exitCode", 0)
    output = response.get("output", "")

    # Check if this is a build command
    build_commands = ["npm run build", "npx tsc", "next build", "npm run type-check"]
    is_build_command = any(cmd in command for cmd in build_commands)

    if is_build_command and exit_code != 0:
        # Build failed - trigger self-correction
        logger.warning(f"Build failed (exit code {exit_code}), triggering self-correction")
        return {
            "systemMessage": f"""## Build Failed - Self-Correction Required

The build command failed with exit code {exit_code}.

### Error Output:
```
{output[:2000]}
```

### Required Actions:
1. **Read the error carefully** - Understand the root cause before changing code
2. **If error involves Next.js/React/library behavior you're unsure about:**
   - Use `mcp__context7__resolve-library-id` to find the library
   - Use `mcp__context7__get-library-docs` to get current documentation
3. Use the `code-reviewer` subagent (via Task tool) to analyze these errors
4. Use the `error-fixer` subagent (via Task tool) to fix each identified issue
5. Run the build again to verify fixes

### Context7 Example (for framework questions):
```
mcp__context7__resolve-library-id with libraryName: "nextjs"
mcp__context7__get-library-docs with libraryId: "/vercel/next.js" and topic: "the specific error topic"
```

Do NOT proceed to preview until the build succeeds. Do NOT guess - look up docs if unsure.
"""
        }

    return {}


async def log_tool_usage(
    input_data: dict,
    tool_use_id: str | None,
    context: dict
) -> dict:
    """
    PreToolUse hook - logs all tool calls for debugging and monitoring.
    """
    tool_name = input_data.get("tool_name", "unknown")
    tool_input = input_data.get("tool_input", {})

    # Log the tool call (truncate long inputs)
    input_str = str(tool_input)
    if len(input_str) > 200:
        input_str = input_str[:200] + "..."

    logger.info(f"[HOOK] Tool call: {tool_name}, input: {input_str}")

    return {}


# Track discovery state per session for soft-warning hook
_discovery_state: dict[str, dict] = {}  # session_id -> {"explored": bool, "warned": bool}


async def remind_discovery_before_build(
    input_data: dict,
    tool_use_id: str | None,
    context: dict
) -> dict:
    """
    PreToolUse hook - reminds agent to run discovery if skipped.
    Soft warning: injects system message but allows proceeding.
    """
    tool_name = input_data.get("tool_name", "unknown")
    session_id = context.get("session_id", "default")

    # Initialize state for session
    if session_id not in _discovery_state:
        _discovery_state[session_id] = {"explored": False, "warned": False}

    state = _discovery_state[session_id]

    # Mark discovery complete when data-explorer Task is invoked
    if tool_name == "Task":
        task_input = input_data.get("tool_input", {})
        if "data-explorer" in str(task_input):
            state["explored"] = True
            logger.info(f"[HOOK] Discovery marked complete for session {session_id}")
            return {}

    # Warn once if Write/Edit used without discovery (soft warning - allows proceeding)
    gated_tools = ["Write", "Edit", "mcp__sandbox__sandbox_write_file"]
    if tool_name in gated_tools and not state["explored"] and not state["warned"]:
        state["warned"] = True
        logger.info(f"[HOOK] Soft warning: Write/Edit without discovery for session {session_id}")
        return {
            "systemMessage": """## Reminder: Discovery Phase

You're about to write code without exploring available data first.

Consider using the `data-explorer` subagent to:
- Discover available Keboola tables
- Understand data schemas
- Confirm requirements with user

If you've already discussed requirements with the user, proceed with building."""
        }

    return {}


# Hook configuration
HOOKS = {
    "PreToolUse": [
        HookMatcher(hooks=[log_tool_usage, remind_discovery_before_build]),
    ],
    "PostToolUse": [
        HookMatcher(matcher="Bash", hooks=[validate_build_result]),
    ],
}


# =============================================================================
# PERMISSION CALLBACK - Dynamic tool access control
# =============================================================================

async def permission_callback(
    tool_name: str,
    input_data: dict,
    context: dict
) -> dict:
    """
    Dynamic permission control for tool usage.

    This callback validates tool calls and can:
    - Allow the call to proceed
    - Deny the call with a message
    - Modify the input (e.g., sanitize paths)

    Returns:
        dict with "behavior" key: "allow" or "deny"
        Optional "message" for deny
        Optional "updatedInput" for modified input
    """
    # Block dangerous Bash commands
    if tool_name == "Bash":
        command = input_data.get("command", "")

        # Dangerous patterns that should never be allowed
        dangerous_patterns = [
            "rm -rf /",
            "rm -rf ~",
            "rm -rf *",
            "sudo ",
            "> /dev/",
            "mkfs",
            "dd if=",
            ":(){:|:&};:",  # Fork bomb
            "chmod -R 777 /",
            "curl | bash",
            "wget | bash",
        ]

        for pattern in dangerous_patterns:
            if pattern in command:
                logger.warning(f"[PERMISSION] Blocked dangerous command: {command}")
                return {
                    "behavior": "deny",
                    "message": f"Dangerous command blocked: {pattern}"
                }

        # Warn about potentially dangerous commands (but allow them)
        warning_patterns = ["rm -rf", "chmod 777", "npm run", "npx"]
        for pattern in warning_patterns:
            if pattern in command:
                logger.info(f"[PERMISSION] Allowing potentially risky command: {command}")

    # Block access to sensitive files
    if tool_name in ["Read", "Write", "Edit"]:
        file_path = input_data.get("file_path", "")

        # Sensitive file patterns
        sensitive_patterns = [
            ".env",
            "credentials",
            "secrets",
            ".git/config",
            "id_rsa",
            ".ssh/",
            "password",
            ".npmrc",
        ]

        file_path_lower = file_path.lower()
        for pattern in sensitive_patterns:
            if pattern in file_path_lower:
                logger.warning(f"[PERMISSION] Blocked access to sensitive file: {file_path}")
                return {
                    "behavior": "deny",
                    "message": f"Access to sensitive file denied: {file_path}"
                }

    # Allow all other operations
    return {"behavior": "allow"}


# =============================================================================
# KEBOOLA CONTEXT - Dynamically loaded from environment
# =============================================================================

def get_keboola_context() -> str:
    """Get Keboola context for system prompt if credentials are configured."""
    kbc_token = os.getenv("KBC_TOKEN", "")
    kbc_url = os.getenv("KBC_URL", "")
    workspace_id = os.getenv("WORKSPACE_ID", "")
    branch_id = os.getenv("BRANCH_ID", "")

    if not kbc_token or kbc_token == "xxx":
        return ""

    return f"""
## Keboola Storage API Access

You have access to Keboola Storage API for reading data from the user's Keboola project.

**Credentials (available as environment variables in sandbox):**
- `KBC_TOKEN`: Storage API token (set)
- `KBC_URL`: `{kbc_url}`
- `WORKSPACE_ID`: `{workspace_id}`
- `BRANCH_ID`: `{branch_id}`

### CRITICAL: Use JSON Format, Not CSV
CSV parsing fails with complex data (HTML, nested quotes). **Always use `format=json`:**

### CRITICAL: Maximum 1000 Rows Per Request
The API silently returns empty data if limit > 1000. Always use `limit=1000` max.

**How to use Keboola data:**

1. **List buckets:**
```bash
curl -s -H "X-StorageApi-Token: $KBC_TOKEN" "{kbc_url}v2/storage/buckets" | jq '.[] | {{id, name, description}}'
```

2. **List tables in a bucket:**
```bash
curl -s -H "X-StorageApi-Token: $KBC_TOKEN" "{kbc_url}v2/storage/buckets/BUCKET_ID/tables" | jq '.[] | {{id, name, rowsCount}}'
```

3. **Preview table data (ALWAYS use format=json and limit<=1000):**
```bash
curl -s -H "X-StorageApi-Token: $KBC_TOKEN" \\
  "{kbc_url}v2/storage/tables/TABLE_ID/data-preview?limit=1000&format=json"
```

4. **For larger datasets, paginate:**
```bash
# Page 1
curl -s -H "X-StorageApi-Token: $KBC_TOKEN" \\
  "{kbc_url}v2/storage/tables/TABLE_ID/data-preview?limit=1000&offset=0&format=json"
# Page 2
curl -s -H "X-StorageApi-Token: $KBC_TOKEN" \\
  "{kbc_url}v2/storage/tables/TABLE_ID/data-preview?limit=1000&offset=1000&format=json"
```

**IMPORTANT:** When user asks about "data in the project" or "Keboola data", use these API calls to explore what tables are available and build apps that visualize that data.
"""


logger = logging.getLogger(__name__)


class AppBuilderAgent:
    """
    AppBuilderAgent wraps Claude Agent SDK to provide agentic workflow
    for building Next.js/React/TypeScript applications in sandboxes.

    PHASE 2: Uses native Claude Code tools for LOCAL mode:
    - Read, Write, Edit for file operations
    - Bash for command execution
    - Glob, Grep for file search
    - MCP only for E2B-specific operations (preview URL, dev server)
    """

    def __init__(self, session_id: Optional[str] = None, on_event: Optional[Callable] = None):
        """
        Initialize the AppBuilderAgent.

        Args:
            session_id: Unique session identifier for logging context
            on_event: Optional callback for frontend notifications.
                     Called with event dict: {"type": "...", ...}
        """
        self.session_id = session_id or "unknown"
        self.on_event = on_event
        self.client: Optional[ClaudeSDKClient] = None
        self.sandbox_manager = None
        self.mcp_server = None
        self._initialized = False
        self._sandbox_notified = False
        self._sandbox_path: Optional[Path] = None

        # Initialize session logger
        self.slogger = get_session_logger(self.session_id)
        self.slogger.log_agent("INIT", "AppBuilderAgent created (Phase 2: native tools)")

        logger.info(f"[{self.session_id}] AppBuilderAgent created")

    def _get_sandbox_path(self) -> Path:
        """Get the sandbox directory path for this session."""
        base_dir = Path(tempfile.gettempdir()) / "app-builder"
        return base_dir / self.session_id

    async def initialize(self) -> None:
        """
        Initialize the Claude SDK client.

        In LOCAL mode: Uses native Claude Code tools with cwd set to sandbox path.
        In E2B mode: Falls back to MCP tools for sandbox operations.
        """
        if self._initialized:
            logger.debug(f"[{self.session_id}] Agent already initialized, skipping")
            return

        self.slogger.log_agent("INIT_START", "initializing agent...")
        logger.info(f"[{self.session_id}] Initializing agent...")

        mode = get_sandbox_mode()
        model = os.getenv("CLAUDE_MODEL", DEFAULT_MODEL)
        logger.info(f"[{self.session_id}] Using sandbox mode: {mode}, model: {model}")

        if mode == "local":
            await self._initialize_local_mode(model)
        else:
            await self._initialize_e2b_mode(model)

        self._initialized = True
        self.slogger.log_agent("INIT_DONE", f"model={model}, mode={mode}")
        logger.info(f"[{self.session_id}] Agent initialized successfully")

    async def _initialize_local_mode(self, model: str) -> None:
        """Initialize agent for LOCAL mode with native tools."""

        # Get sandbox path and ensure it exists
        self._sandbox_path = self._get_sandbox_path()
        self._sandbox_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"[{self.session_id}] Sandbox path: {self._sandbox_path}")

        # Initialize sandbox manager for E2B-specific tools only
        self.sandbox_manager = create_sandbox_manager(session_id=self.session_id)

        # IMPORTANT: Initialize the sandbox to allocate a port
        # This ensures preview_url is available even though native tools don't go through our manager
        await self.sandbox_manager.ensure_sandbox()
        logger.info(f"[{self.session_id}] Sandbox initialized, allocated port: {self.sandbox_manager._allocated_port}")

        # Create minimal MCP server with only E2B-specific tools
        self.mcp_server = create_e2b_only_server(self.sandbox_manager, session_id=self.session_id)

        # Configure Claude Agent SDK with native tools and subagents
        options = ClaudeAgentOptions(
            # Set working directory to sandbox path - native tools will operate here
            cwd=str(self._sandbox_path),

            # Use Claude Code preset with our app builder additions
            system_prompt={
                "type": "preset",
                "preset": "claude_code",
                "append": SYSTEM_PROMPT_APPEND,
            },

            model=model,

            # Native tools + E2B MCP tools + Context7 MCP tools + Task for subagents
            allowed_tools=[
                # Native Claude Code tools
                "Read", "Write", "Edit",
                "Bash",
                "Glob", "Grep",
                "Task",  # For spawning subagents
                # E2B-specific MCP tools (note: includes 'sandbox_' prefix from tool function names)
                "mcp__e2b__sandbox_get_preview_url",
                "mcp__e2b__sandbox_start_dev_server",
                # Context7 MCP tools for live documentation
                "mcp__context7__resolve-library-id",
                "mcp__context7__get-library-docs",
            ],

            # MCP servers: E2B for sandbox ops, Context7 for live docs
            mcp_servers={
                "e2b": self.mcp_server,
                "context7": {
                    "command": "npx",
                    "args": ["-y", "@upstash/context7-mcp@latest"],
                },
            },

            # Specialized subagents for code review, error fixing, and component generation
            agents=AGENTS,

            # Hooks for self-correction and logging
            hooks=HOOKS,

            # Permission callback for dynamic tool access control
            can_use_tool=permission_callback,

            # Accept edits automatically for faster workflow
            permission_mode="acceptEdits",
        )

        # Create and connect client
        self.client = ClaudeSDKClient(options)
        await self.client.connect()

    async def _initialize_e2b_mode(self, model: str) -> None:
        """Initialize agent for E2B cloud mode with MCP tools."""

        # Initialize sandbox manager with session context
        self.sandbox_manager = create_sandbox_manager(session_id=self.session_id)

        # Create full MCP tools server for E2B operations
        self.mcp_server = create_sandbox_tools_server(self.sandbox_manager, session_id=self.session_id)

        # Use unified system prompt (same as local mode) with Keboola context
        system_prompt = SYSTEM_PROMPT_APPEND + get_keboola_context()

        # Configure Claude Agent SDK with MCP tools + Context7 + subagents + hooks
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            model=model,
            mcp_servers={
                "sandbox": self.mcp_server,
                # Context7 for live documentation lookup (same as local mode)
                "context7": {
                    "command": "npx",
                    "args": ["-y", "@upstash/context7-mcp@latest"],
                },
            },
            allowed_tools=[
                "mcp__sandbox__sandbox_write_file",
                "mcp__sandbox__sandbox_read_file",
                "mcp__sandbox__sandbox_list_files",
                "mcp__sandbox__sandbox_run_command",
                "mcp__sandbox__sandbox_install_packages",
                "mcp__sandbox__sandbox_get_preview_url",
                "mcp__sandbox__sandbox_start_dev_server",
                # Context7 MCP tools for live documentation
                "mcp__context7__resolve-library-id",
                "mcp__context7__get-library-docs",
                # Task tool for subagents
                "Task",
            ],
            # Add subagents and hooks (same as local mode)
            agents=AGENTS,
            hooks=HOOKS,
            permission_mode="acceptEdits",
        )

        # Create and connect client
        self.client = ClaudeSDKClient(options)
        await self.client.connect()

    async def chat(self, message: str) -> AsyncIterator[dict]:
        """
        Process a user message and stream response events.

        Args:
            message: User's message/instruction

        Yields:
            Event dicts with types:
            - {"type": "text", "content": "..."} - Text response chunks
            - {"type": "tool_use", "tool": "...", "input": {...}} - Tool calls
            - {"type": "tool_result", "tool": "...", "result": {...}} - Tool results
            - {"type": "done", "preview_url": "..."} - Completion with preview URL

        Raises:
            RuntimeError: If initialize() hasn't been called
        """
        if not self._initialized or not self.client:
            logger.error(f"[{self.session_id}] chat() called before initialization")
            raise RuntimeError(
                "AppBuilderAgent not initialized. Call initialize() first."
            )

        # Generate message ID for tracking
        msg_id = f"req_{int(time.time()*1000)}"
        self.slogger.log_agent("CHAT_START", f"msg_id={msg_id}, len={len(message)}")
        logger.info(f"[{self.session_id}] Processing chat message: {message[:100]}{'...' if len(message) > 100 else ''}")

        # Send message to Claude
        await self.client.query(message)

        # Track if we've started a dev server to get preview URL
        preview_url = None

        # Track blocks for summary logging
        text_block_count = 0
        tool_use_count = 0
        tool_result_count = 0

        # Stream response from Claude
        last_block_type = None
        async for msg in self.client.receive_response():
            if isinstance(msg, AssistantMessage):
                # Process message content blocks
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        # Add separator if coming after tool use/result for visual break
                        text = block.text
                        if last_block_type in ('tool_result', 'tool_use'):
                            text = "\n\n---\n\n" + text

                        # Log text block
                        self.slogger.log_agent("TEXT_BLOCK", f"len={len(block.text)}")
                        text_block_count += 1

                        event = {
                            "type": "text",
                            "content": text
                        }
                        if self.on_event:
                            self.on_event(event)
                        yield event
                        last_block_type = 'text'

                    elif isinstance(block, ToolUseBlock):
                        # Check if sandbox was created (lazy init) and notify
                        if not self._sandbox_notified and self.sandbox_manager and self.sandbox_manager.is_initialized:
                            self._sandbox_notified = True
                            sandbox_event = {
                                "type": "sandbox_ready",
                                "sandbox_id": self.sandbox_manager.sandbox_id
                            }
                            if self.on_event:
                                self.on_event(sandbox_event)
                            yield sandbox_event

                        # Log tool use block with detailed input info
                        input_keys = list(block.input.keys()) if isinstance(block.input, dict) else str(type(block.input))
                        self.slogger.log_agent("TOOL_USE_BLOCK", f"tool={block.name}, id={block.id}, input_keys={input_keys}")
                        tool_use_count += 1

                        # Debug logging for Write tool
                        if block.name == "Write":
                            logger.info(f"[{self.session_id}] Write tool input: {list(block.input.keys()) if isinstance(block.input, dict) else block.input}")

                        event = {
                            "type": "tool_use",
                            "tool": block.name,
                            "input": block.input
                        }
                        if self.on_event:
                            self.on_event(event)
                        yield event
                        last_block_type = 'tool_use'

                    elif isinstance(block, ToolResultBlock):
                        # Log tool result block
                        content_type = type(block.content).__name__
                        content_preview = str(block.content)[:200] if block.content else "None"
                        self.slogger.log_agent("TOOL_RESULT_BLOCK", f"id={block.tool_use_id}, content_type={content_type}")
                        tool_result_count += 1

                        event = {
                            "type": "tool_result",
                            "tool": block.tool_use_id,
                            "result": block.content
                        }
                        if self.on_event:
                            self.on_event(event)
                        yield event
                        last_block_type = 'tool_result'

                        # Extract preview URL if available
                        content = block.content
                        preview_url = self._extract_preview_url(content) or preview_url

        # If we didn't get preview URL from tool results, try sandbox manager
        if not preview_url and self.sandbox_manager:
            try:
                # LocalSandboxManager has preview_url property, E2B SandboxManager has get_preview_url method
                if hasattr(self.sandbox_manager, 'preview_url'):
                    manager_preview_url = self.sandbox_manager.preview_url
                elif hasattr(self.sandbox_manager, 'get_preview_url') and self.sandbox_manager.is_initialized:
                    manager_preview_url = await self.sandbox_manager.get_preview_url()
                else:
                    manager_preview_url = None

                if manager_preview_url:
                    preview_url = manager_preview_url
                    self.slogger.log_agent("PREVIEW_URL_FOUND", f"source=sandbox_manager, url={preview_url}")
            except Exception as e:
                logger.warning(f"[{self.session_id}] Could not get preview URL from sandbox manager: {e}")

        # Send done event with preview URL if available
        done_event = {
            "type": "done",
            "preview_url": preview_url
        }
        if self.on_event:
            self.on_event(done_event)

        # Log chat completion
        self.slogger.log_agent(
            "CHAT_END",
            f"msg_id={msg_id}, text_blocks={text_block_count}, "
            f"tool_uses={tool_use_count}, tool_results={tool_result_count}, "
            f"preview_url={preview_url}"
        )
        logger.info(f"[{self.session_id}] Chat completed, preview_url={preview_url}")
        yield done_event

    def _extract_preview_url(self, content) -> Optional[str]:
        """Extract preview URL from tool result content."""
        # Handle dict content
        if isinstance(content, dict):
            if "preview_url" in content:
                return content["preview_url"]
            elif "url" in content:
                return content["url"]

        # Handle list content
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if "preview_url" in item:
                        return item["preview_url"]
                    elif "url" in item:
                        return item["url"]
                    elif "text" in item and isinstance(item["text"], str):
                        text = item["text"]
                        if "http://localhost:" in text:
                            match = re.search(r'http://localhost:\d+', text)
                            if match:
                                return match.group(0)

        # Handle string content
        elif isinstance(content, str) and "http://localhost:" in content:
            match = re.search(r'http://localhost:\d+', content)
            if match:
                return match.group(0)

        return None

    async def cleanup(self) -> None:
        """
        Cleanup resources (close MCP server, cleanup sandboxes, etc.)
        Should be called when done using the agent.
        """
        logger.info(f"[{self.session_id}] Cleaning up agent resources...")
        try:
            # Disconnect Claude SDK client
            if self.client:
                await self.client.disconnect()
                self.client = None
                logger.debug(f"[{self.session_id}] Claude SDK client disconnected")

            # Cleanup sandbox manager
            if self.sandbox_manager:
                await self.sandbox_manager.destroy()
                self.sandbox_manager = None
                logger.debug(f"[{self.session_id}] Sandbox manager destroyed")

            # Close MCP server
            if self.mcp_server:
                if hasattr(self.mcp_server, 'close'):
                    await self.mcp_server.close()
                self.mcp_server = None
                logger.debug(f"[{self.session_id}] MCP server closed")

            self._initialized = False
            logger.info(f"[{self.session_id}] Agent cleanup completed")

        except Exception as e:
            logger.error(f"[{self.session_id}] Error during cleanup: {e}", exc_info=True)
