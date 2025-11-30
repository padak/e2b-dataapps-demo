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
from .prompts.data_platform import DATA_PLATFORM_PROMPT
from .integrations.keboola_mcp import (
    get_keboola_mcp_config,
    get_essential_keboola_tools,
    is_keboola_configured,
)

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

### Your Capabilities

**Native Tools (prefer these for file operations):**
- `Read` - Read file contents (also supports images)
- `Write` - Create or overwrite files
- `Edit` - Make surgical changes to files (old_string → new_string) - PREFER THIS over Write for changes
- `Bash` - Run shell commands (npm, node, etc.) with timeout support
- `Glob` - Find files by pattern (e.g., `**/*.tsx`)
- `Grep` - Search file contents with regex

**Custom Tools (for sandbox-specific operations):**
- `mcp__e2b__sandbox_get_preview_url` - Get the live preview URL
- `mcp__e2b__sandbox_start_dev_server` - Start the Next.js dev server (ALWAYS use this, never run npm run dev via Bash!)

### Workflow

1. **Create** - Use `Write` to create new files
2. **Edit** - Use `Edit` for modifications (NOT Write for existing files)
3. **Verify** - Run `npm run build` via Bash to check for errors
4. **Fix** - If errors, read the files and fix them
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

### Error Handling

If build fails:
1. Read the error message carefully
2. Use Glob/Grep to find the problematic files
3. Use Read to examine the context
4. Use Edit to fix the issues surgically
5. Run build again to verify

### Subagents Available

You can delegate tasks to specialized subagents using the Task tool:
- `security-reviewer`: **REQUIRED** - Reviews code for security vulnerabilities. Must run before dev server.
- `code-reviewer`: Reviews TypeScript/React code for errors. Use when build fails.
- `error-fixer`: Fixes specific code errors identified by code-reviewer.
- `component-generator`: Generates React components with TypeScript and Tailwind.

### CRITICAL: Security Review Before Preview

**Before starting the dev server, you MUST run a security review:**

1. After build succeeds, use Task tool with `subagent_type="security-reviewer"`:
   ```
   Task tool:
     subagent_type: "security-reviewer"
     prompt: "Review all source files in this project for security vulnerabilities.
              Check for SQL injection, data exfiltration, credential leaks, and dangerous patterns."
   ```

2. Parse the JSON response from security-reviewer:
   - If `safe: true` → call `mcp__e2b__mark_security_review_passed` with `passed: true`
   - If `safe: false` with HIGH severity issues → fix the issues first, then re-run review

3. Only after security review passes can you start the dev server.

**What security-reviewer checks:**
- SQL injection (user input in queries)
- Data exfiltration (unauthorized external API calls)
- Credential leaks (logging process.env, exposing secrets)
- Dangerous patterns (eval, dangerouslySetInnerHTML with user input)

""" + DATA_PLATFORM_PROMPT

# =============================================================================
# SUBAGENTS - Specialized agents for different tasks
# =============================================================================

AGENTS = {
    "security-reviewer": AgentDefinition(
        description="Reviews generated code for security issues. Use before starting dev server.",
        prompt="""You are a security code reviewer for generated Next.js applications.

## Your Task
Review the generated application code for security vulnerabilities:

1. **Data Exfiltration** - Code sending data to external endpoints
   - Unauthorized fetch/axios calls to non-Keboola domains
   - WebSocket connections to unknown servers
   - Image/script sources from untrusted origins

2. **Credential Leaks** - Logging or exposing environment variables
   - console.log with process.env values
   - Exposing secrets in client-side code
   - Credentials in error messages

3. **SQL Injection** - User input in SQL queries without sanitization
   - String concatenation: `SELECT * FROM ${userInput}`
   - Template literals with user input in queries
   - Dynamic table/column names from user input
   - Missing parameterized queries

4. **Unauthorized Actions** - Code doing things user didn't request
   - Hidden API calls
   - Unexpected data modifications
   - Covert data collection

5. **Dangerous Patterns**
   - eval() with user input
   - dangerouslySetInnerHTML with user input
   - Dynamic require/import with user input
   - Unvalidated redirects

## Safe Patterns (OK)
- Parameterized queries with placeholders
- Whitelisted values for dynamic SQL parts
- Input validation before query
- Fetch to Keboola Query Service API
- Environment variables read server-side only

## Process
1. Use Glob to find all source files (*.ts, *.tsx, *.js)
2. Use Grep to search for dangerous patterns
3. Use Read to examine suspicious code in context
4. Report findings in JSON format

## Output Format
Return ONLY valid JSON (no markdown, no extra text):
{
  "safe": true/false,
  "issues": [
    {
      "severity": "high|medium|low",
      "type": "sql_injection|exfiltration|credential_leak|unauthorized_action|dangerous_pattern",
      "file": "path/to/file.tsx",
      "line": 42,
      "description": "Description of the issue",
      "code_snippet": "The problematic code",
      "fix_suggestion": "How to fix it"
    }
  ],
  "summary": "Brief assessment of overall security posture"
}

## Severity Guidelines
- **high**: Immediate security risk (SQL injection, credential leak, data exfiltration)
- **medium**: Potential risk that needs attention (unsafe patterns, missing validation)
- **low**: Best practice violation (minor security hygiene issues)

Mark as safe=false if ANY high severity issue is found.
""",
        tools=["Read", "Glob", "Grep"],
        model="haiku"  # Cost-effective for review tasks
    ),

    "code-reviewer": AgentDefinition(
        description="Reviews TypeScript/React code for errors. Use when build fails or you need code review.",
        prompt="""You are an expert TypeScript/React code reviewer.

## Your Task
Analyze error messages and source code to identify issues.

## Process
1. Read the error message carefully
2. Use Grep to find the problematic code
3. Use Read to examine the full context
4. Identify the exact issue

## Output Format
For each issue found, report in this format:
```
FILE: path/to/file.tsx
LINE: 42
ISSUE: Brief description of the problem
CONFIDENCE: 85%
FIX: Suggested fix (be specific about what to change)
```

## Rules
- Only report issues with confidence >= 80%
- Focus on actual errors, not style preferences
- Be specific about line numbers and fixes
- Check for: missing imports, type errors, syntax errors, undefined variables
""",
        tools=["Read", "Grep", "Glob"],
        model="haiku"  # Cost-effective for review tasks
    ),

    "error-fixer": AgentDefinition(
        description="Fixes specific code errors identified by code-reviewer.",
        prompt="""You are a precise code fixer.

## Your Task
Apply specific fixes to code based on error analysis.

## Process
1. Read the current file content
2. Use Edit to make surgical changes (old_string → new_string)
3. Verify the change makes sense in context

## Rules
- Use Edit tool, NOT Write (preserves more context)
- Make minimal changes - fix only what's broken
- One fix at a time
- Preserve existing code style and formatting
- After fixing, briefly explain what you changed

## Common Fixes
- Missing imports: Add the import at the top
- Type errors: Add proper type annotations
- Undefined variables: Check for typos or add declarations
- Syntax errors: Fix brackets, semicolons, etc.
""",
        tools=["Read", "Edit"],
        model="sonnet"
    ),

    "component-generator": AgentDefinition(
        description="Generates React components with TypeScript and Tailwind. Use for creating new UI components.",
        prompt="""You are a React component specialist.

## Stack
- React 18 with hooks
- TypeScript strict mode
- Tailwind CSS for styling
- shadcn/ui for UI primitives

## Component Structure
```typescript
'use client'  // Only if using hooks/state/effects

import { ComponentType } from 'react'

interface Props {
  // Define all props with proper types
}

export default function ComponentName({ prop1, prop2 }: Props) {
  // Implementation
  return (
    <div className="...">
      {/* JSX */}
    </div>
  )
}
```

## Rules
- Use 'use client' ONLY for components with state, effects, or event handlers
- Export as default
- Include proper TypeScript types for all props
- Make responsive with Tailwind (mobile-first)
- Use semantic HTML elements
- Include loading and error states where appropriate
- Use Tailwind's design system (spacing: 4, 8, 16..., colors: slate, blue...)
""",
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
1. Use the `code-reviewer` subagent (via Task tool) to analyze these errors
2. Use the `error-fixer` subagent (via Task tool) to fix each identified issue
3. Run the build again to verify fixes

Example Task tool usage:
```
Use Task tool with subagent_type="code-reviewer" to analyze the build errors above.
```

Do NOT proceed to preview until the build succeeds.
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


# Import security review state management from dedicated module
from .security.security_review import (
    mark_security_review_completed,
    reset_security_review,
    get_security_review_state,
)


async def require_security_review(
    input_data: dict,
    tool_use_id: str | None,
    context: dict
) -> dict:
    """
    PreToolUse hook - requires security review before starting dev server.

    This hook intercepts sandbox_start_dev_server calls and checks if
    a security review has been completed. If not, it blocks the call
    and instructs the agent to run security-reviewer first.
    """
    tool_name = input_data.get("tool_name", "unknown")

    # Only intercept dev server start
    if tool_name != "mcp__e2b__sandbox_start_dev_server":
        return {}

    # Get session ID from context
    session_id = context.get("session_id", "unknown")

    # Check if security review was completed for this session
    session_state = get_security_review_state(session_id)
    review_completed = session_state.get("security_review_completed", False)
    review_passed = session_state.get("security_review_passed", False)

    if review_completed and review_passed:
        # Security review passed - allow dev server to start
        logger.info(f"[SECURITY] Session {session_id}: Security review passed, allowing dev server start")
        return {}

    if review_completed and not review_passed:
        # Security review failed - block and require fixes
        issues_summary = session_state.get("issues_summary", "Unknown issues")
        logger.warning(f"[SECURITY] Session {session_id}: Security review failed, blocking dev server")
        return {
            "decision": "block",
            "reason": f"""## Security Review Failed - Fixes Required

The security review found issues that must be fixed before starting the dev server.

### Issues Found:
{issues_summary}

### Required Actions:
1. Fix all HIGH severity security issues identified
2. Run security-reviewer again to verify fixes
3. Only then start the dev server

Do NOT attempt to start the dev server until security issues are resolved.
"""
        }

    # Security review not yet done - block and require review
    logger.info(f"[SECURITY] Session {session_id}: Security review required before dev server start")
    return {
        "decision": "block",
        "reason": """## Security Review Required

Before starting the dev server, you MUST run a security review of the generated code.

### Required Actions:
1. Use the `security-reviewer` subagent (via Task tool) to scan the codebase:
   ```
   Task tool with subagent_type="security-reviewer"
   Prompt: "Review all source files in this project for security vulnerabilities"
   ```

2. If the review returns `safe: true`:
   - Call `mark_security_review_passed` tool to record success
   - Then start the dev server

3. If the review returns `safe: false` with HIGH severity issues:
   - Fix the identified issues
   - Run security-reviewer again
   - Only proceed when all HIGH severity issues are resolved

This security check protects against SQL injection, data exfiltration, and credential leaks.
"""
    }


async def invalidate_security_review_on_code_change(
    input_data: dict,
    tool_use_id: str | None,
    context: dict
) -> dict:
    """
    PostToolUse hook - invalidates security review when code is modified.

    If files are changed after security review passed, the review is reset
    to require a new security check before starting the dev server.
    """
    tool_name = input_data.get("tool_name", "unknown")

    # Only care about file modification tools
    if tool_name not in ["Write", "Edit"]:
        return {}

    # Get session ID from context
    session_id = context.get("session_id", "unknown")

    # Check if there's a completed security review for this session
    session_state = get_security_review_state(session_id)
    if session_state.get("security_review_completed", False):
        # Code was modified after security review - invalidate it
        reset_security_review(session_id)
        logger.info(f"[SECURITY] Session {session_id}: Security review invalidated due to code change via {tool_name}")

        return {
            "systemMessage": """## Security Review Invalidated

Code was modified after the security review passed. You must run the security review again before starting the dev server.

Use Task tool with `subagent_type="security-reviewer"` to re-scan the updated code.
"""
        }

    return {}


# Hook configuration
HOOKS = {
    "PreToolUse": [
        HookMatcher(hooks=[log_tool_usage]),
        # Security review required before starting dev server
        HookMatcher(
            matcher="mcp__e2b__sandbox_start_dev_server",
            hooks=[require_security_review]
        ),
    ],
    "PostToolUse": [
        HookMatcher(matcher="Bash", hooks=[validate_build_result]),
        # Invalidate security review when code changes
        HookMatcher(matcher="Write", hooks=[invalidate_security_review_on_code_change]),
        HookMatcher(matcher="Edit", hooks=[invalidate_security_review_on_code_change]),
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


# Legacy system prompt for E2B mode (kept for backwards compatibility)
LEGACY_SYSTEM_PROMPT = """You are an expert Next.js/React/TypeScript developer building data-driven web applications in an isolated sandbox environment.

CRITICAL: You are working in a sandbox environment. ALL commands and file operations run INSIDE this sandbox. NEVER tell the user to run commands themselves - YOU must run everything in the sandbox using your tools.

Your role is to help users build modern, production-quality web applications using:
- **Next.js 14+** with App Router
- **React 18+** with TypeScript
- **Tailwind CSS** for styling
- **shadcn/ui** for UI components
- **Data visualization** libraries (recharts, plotly, etc.)

## Your Capabilities

You have access to sandbox tools that allow you to:
1. **Create files** - Write code files (components, pages, utilities, configs)
2. **Execute commands** - Run npm/yarn commands, build, test, install packages
3. **Read files** - Inspect existing code and configurations
4. **List files** - Explore project structure
5. **Install packages** - Add npm dependencies
6. **Run dev server** - Start Next.js development server with hot reload
7. **Get preview URL** - Access the live running application

## CRITICAL: Running Applications

When you finish building an application, you MUST follow this EXACT sequence:
1. Run `npm install` using sandbox_run_command to install dependencies
2. Use `sandbox_start_dev_server` tool to start the Next.js dev server - this runs in background and returns the preview URL
3. The preview URL from sandbox_start_dev_server is the FINAL URL - share it with the user

**CRITICAL RULES - VIOLATION WILL CAUSE ERRORS:**

1. **NEVER run `npm run dev` via sandbox_run_command** - This will timeout and fail!
   - GOOD: `sandbox_start_dev_server()` ✓

2. **Port is AUTO-ALLOCATED (never 3000)** - Port 3000 is reserved for our frontend!

3. **Only call sandbox_start_dev_server ONCE**

NEVER tell the user to run commands themselves. YOU run everything in the sandbox.

## CRITICAL: next.config.js for Preview

ALWAYS create this next.config.js:

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

        # Build MCP servers configuration
        mcp_servers = {
            "e2b": self.mcp_server
        }

        # Build allowed tools list
        allowed_tools = [
            # Native Claude Code tools
            "Read", "Write", "Edit",
            "Bash",
            "Glob", "Grep",
            "Task",  # For spawning subagents
            # E2B-specific MCP tools
            "mcp__e2b__sandbox_get_preview_url",
            "mcp__e2b__sandbox_start_dev_server",
            "mcp__e2b__mark_security_review_passed",  # Security review confirmation
        ]

        # Add Keboola MCP server if configured
        keboola_config = get_keboola_mcp_config()
        if keboola_config:
            mcp_servers["keboola"] = keboola_config
            allowed_tools.extend(get_essential_keboola_tools())
            logger.info(f"[{self.session_id}] Keboola MCP enabled with {len(get_essential_keboola_tools())} tools")
        else:
            logger.info(f"[{self.session_id}] Keboola MCP not configured (missing credentials)")

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

            # Native tools + MCP tools + Task for subagents
            allowed_tools=allowed_tools,

            # MCP servers (E2B + Keboola if configured)
            mcp_servers=mcp_servers,

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
        """Initialize agent for E2B cloud mode with MCP tools (legacy approach)."""

        # Initialize sandbox manager with session context
        self.sandbox_manager = create_sandbox_manager(session_id=self.session_id)

        # Create full MCP tools server for E2B operations
        self.mcp_server = create_sandbox_tools_server(self.sandbox_manager, session_id=self.session_id)

        # Configure Claude Agent SDK with MCP tools (legacy approach)
        options = ClaudeAgentOptions(
            system_prompt=LEGACY_SYSTEM_PROMPT,
            model=model,
            mcp_servers={
                "sandbox": self.mcp_server
            },
            allowed_tools=[
                "mcp__sandbox__sandbox_write_file",
                "mcp__sandbox__sandbox_read_file",
                "mcp__sandbox__sandbox_list_files",
                "mcp__sandbox__sandbox_run_command",
                "mcp__sandbox__sandbox_install_packages",
                "mcp__sandbox__sandbox_get_preview_url",
                "mcp__sandbox__sandbox_start_dev_server",
            ],
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
            manager_preview_url = self.sandbox_manager.preview_url
            if manager_preview_url:
                preview_url = manager_preview_url
                self.slogger.log_agent("PREVIEW_URL_FOUND", f"source=sandbox_manager, url={preview_url}")

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
