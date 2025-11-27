#!/usr/bin/env python3
"""
AppBuilderAgent - Claude Agent SDK wrapper for Next.js/React/TypeScript app builder.
Provides agentic workflow for building data applications in sandboxes.
"""

import logging
import os
from typing import AsyncIterator, Callable, Optional

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
)

from .sandbox_factory import create_sandbox_manager
from .tools.sandbox_tools import create_sandbox_tools_server

# Default model if not specified in environment
DEFAULT_MODEL = "claude-sonnet-4-5"


def get_sandbox_mode() -> str:
    """Get the current sandbox mode from environment."""
    return os.getenv("SANDBOX_MODE", "local").lower()


SYSTEM_PROMPT_BASE = """You are an expert Next.js/React/TypeScript developer building data-driven web applications in an isolated sandbox environment.

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

## IMPORTANT: Running Applications

When you finish building an application, you MUST:
1. Run `npm install` using sandbox_run_command to install dependencies
2. Use `sandbox_start_dev_server` tool to start the Next.js dev server - this runs in background and returns the preview URL
3. Share the preview URL with the user so they can see their running app in the Preview panel

NEVER tell the user to run commands themselves. YOU run everything in the sandbox.
ALWAYS use sandbox_start_dev_server (not sandbox_run_command) to start the dev server - it handles background execution properly.

## Development Workflow

When building an application, follow this systematic approach:

### 1. Project Setup
- Initialize Next.js project with TypeScript and Tailwind CSS
- Set up the basic project structure (app/, components/, lib/, etc.)
- Install essential dependencies (shadcn/ui, data viz libraries, etc.)

### 2. File Structure
Create a well-organized project:
```
/app
  /layout.tsx          # Root layout
  /page.tsx            # Home page
  /api/                # API routes
/components
  /ui/                 # shadcn/ui components
  /charts/             # Chart components
  /tables/             # Table components
/lib
  /utils.ts            # Utility functions
  /api.ts              # API clients
/types
  /index.ts            # TypeScript types
```

### 3. Code Quality Standards

**TypeScript**
- Use strict type checking
- Define proper interfaces and types
- Avoid `any` - use specific types or `unknown`
- Use proper generics for reusable components

**React Best Practices**
- Use functional components with hooks
- Implement proper error boundaries
- Use React.memo() for expensive components
- Leverage Suspense and loading states
- Use server components by default, client components when needed

**Next.js Patterns**
- Use App Router (app/ directory)
- Implement proper metadata for SEO
- Use server actions for mutations
- Implement proper loading and error states
- Use dynamic imports for code splitting

**Styling**
- Use Tailwind CSS utility classes
- Follow responsive design patterns (mobile-first)
- Use shadcn/ui components for consistency
- Implement dark mode support when appropriate

### 4. Data Handling

**For data visualization apps:**
- Fetch data using server components or API routes
- Implement proper loading states
- Handle errors gracefully with error boundaries
- Use React Query or SWR for client-side data fetching
- Implement proper data transformations
- Add pagination for large datasets

**Common patterns:**
```typescript
// Server component data fetching
async function getData() {
  const res = await fetch('...', { cache: 'no-store' })
  if (!res.ok) throw new Error('Failed to fetch')
  return res.json()
}

// Client component with state
'use client'
import { useState, useEffect } from 'react'

export function DataChart() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchData().then(setData).finally(() => setLoading(false))
  }, [])

  if (loading) return <Skeleton />
  return <Chart data={data} />
}
```

### 5. Component Development

**shadcn/ui Integration**
- Always use shadcn/ui components for UI elements
- Run `npx shadcn-ui@latest add <component>` to add components
- Customize components in `components/ui/` as needed

**Chart Components**
- Use recharts for most charts (built on D3)
- Use plotly.js for advanced interactive visualizations
- Wrap chart libraries in client components ('use client')
- Make charts responsive with proper container sizing

### 6. Running & Validation

Before considering the app complete, YOU MUST:
1. **Install dependencies** - Run `npm install` in the sandbox
2. **Start dev server** - Run `npm run dev &` in the sandbox (background process)
3. **Get preview URL** - Call sandbox_get_preview_url and share it with the user
4. **Verify** - The user will see their app running at the preview URL

DO NOT ask the user to run commands - you have full control of the sandbox!

## Communication Style

When working on tasks:
1. **Be explicit** - Explain what you're doing and why
2. **Show progress** - Update the user as you create files and run commands
3. **Handle errors** - If something fails, explain the error and fix it
4. **Ask when unclear** - If requirements are ambiguous, ask for clarification
5. **Provide context** - Explain architectural decisions

## Example Interactions

**User:** "Build a dashboard showing sales data with charts"

**Your approach:**
1. Create Next.js project with TypeScript
2. Install dependencies (shadcn/ui, recharts)
3. Set up project structure
4. Create data API route or mock data
5. Build chart components (bar chart, line chart, pie chart)
6. Create dashboard layout with responsive grid
7. Add loading states and error handling
8. Start dev server and provide preview URL

**User:** "Add a table with filtering and sorting"

**Your approach:**
1. Install shadcn/ui table component
2. Create table component with TypeScript types
3. Implement filtering logic with state
4. Add sorting functionality
5. Make it responsive (card view on mobile)
6. Test and verify functionality

## Important Notes

- **Always use TypeScript** - No JavaScript files
- **Modern React** - Use hooks, no class components
- **App Router** - Use Next.js 14+ App Router, not Pages Router
- **Responsive** - Every component should work on mobile
- **Accessible** - Use semantic HTML and ARIA labels
- **Performant** - Code split, lazy load, optimize images
- **Type-safe** - Proper TypeScript throughout

## Error Handling

If you encounter errors:
1. Read the error message carefully
2. Check file paths and imports
3. Verify package versions compatibility
4. Ensure all dependencies are installed
5. Check TypeScript types
6. Restart dev server if needed

Remember: Your goal is to build production-quality applications that are maintainable, performant, and delightful to use.
"""

# Local mode specific instructions
LOCAL_MODE_ADDENDUM = """

## LOCAL MODE SPECIFIC INSTRUCTIONS

You are running in LOCAL MODE, not E2B cloud sandbox. Important differences:

1. **File paths**: All files are stored locally under `/tmp/app-builder/{session_id}/`. You should use RELATIVE paths from the project root (e.g., `app/page.tsx`, `package.json`), not absolute paths.

2. **Preview URLs**: When the dev server starts, the preview URL will be `http://localhost:{port}`. The `sandbox_get_preview_url` tool returns the correct localhost URL - USE THIS VALUE, do not construct URLs yourself.

3. **Do NOT generate E2B-style URLs** like `https://3000-{session}.preview.sandbox.anthropic.com`. Those are for cloud sandboxes only. In local mode, always use `http://localhost:{port}`.

4. **Use relative paths** for all file operations. Do NOT use paths starting with `/private/tmp/` or `/tmp/`. Just use relative paths like:
   - `package.json`
   - `app/page.tsx`
   - `components/Button.tsx`

5. **After starting dev server**: Call `sandbox_get_preview_url` to get the correct localhost URL and share that with the user.
"""

# E2B cloud mode specific instructions
E2B_MODE_ADDENDUM = """

## E2B CLOUD MODE INSTRUCTIONS

You are running in E2B cloud sandbox. The preview URLs will be in the format:
`https://{port}-{sandbox_id}.preview.sandbox.anthropic.com`

Use the `sandbox_get_preview_url` tool to get the correct preview URL after starting the dev server.
"""


def get_system_prompt() -> str:
    """Get the full system prompt based on sandbox mode."""
    mode = get_sandbox_mode()
    if mode == "local":
        return SYSTEM_PROMPT_BASE + LOCAL_MODE_ADDENDUM
    else:
        return SYSTEM_PROMPT_BASE + E2B_MODE_ADDENDUM


logger = logging.getLogger(__name__)


class AppBuilderAgent:
    """
    AppBuilderAgent wraps Claude Agent SDK to provide agentic workflow
    for building Next.js/React/TypeScript applications in sandboxes.

    Supports both local sandbox mode (for development) and E2B cloud sandbox mode.
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
        logger.info(f"[{self.session_id}] AppBuilderAgent created")

    async def initialize(self) -> None:
        """
        Initialize the Claude SDK client with MCP sandbox tools.
        Must be called before using chat().
        """
        if self._initialized:
            logger.debug(f"[{self.session_id}] Agent already initialized, skipping")
            return

        logger.info(f"[{self.session_id}] Initializing agent...")

        # Initialize sandbox manager with session context
        self.sandbox_manager = create_sandbox_manager(session_id=self.session_id)

        # Create MCP tools server for sandbox operations
        self.mcp_server = create_sandbox_tools_server(self.sandbox_manager)

        # Get model from environment or use default
        model = os.getenv("CLAUDE_MODEL", DEFAULT_MODEL)
        logger.info(f"[{self.session_id}] Using Claude model: {model}")

        # Configure Claude Agent SDK with mode-specific system prompt
        system_prompt = get_system_prompt()
        logger.info(f"[{self.session_id}] Using sandbox mode: {get_sandbox_mode()}")

        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            model=model,
            mcp_servers={
                "sandbox": self.mcp_server
            },
            # Allow sandbox tools for file operations, command execution, etc.
            # Note: tool names are mcp__{server_name}__{tool_name}
            allowed_tools=[
                "mcp__sandbox__sandbox_write_file",
                "mcp__sandbox__sandbox_read_file",
                "mcp__sandbox__sandbox_list_files",
                "mcp__sandbox__sandbox_run_command",
                "mcp__sandbox__sandbox_install_packages",
                "mcp__sandbox__sandbox_get_preview_url",
                "mcp__sandbox__sandbox_start_dev_server",
            ],
            # Accept edits automatically for faster workflow
            permission_mode="acceptEdits",
        )

        # Create and connect client
        self.client = ClaudeSDKClient(options)
        await self.client.connect()

        self._initialized = True
        logger.info(f"[{self.session_id}] Agent initialized successfully")

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

        logger.info(f"[{self.session_id}] Processing chat message: {message[:100]}{'...' if len(message) > 100 else ''}")

        # Send message to Claude
        await self.client.query(message)

        # Track if we've started a dev server to get preview URL
        preview_url = None

        # Stream response from Claude
        last_block_type = None
        async for msg in self.client.receive_response():
            if isinstance(msg, AssistantMessage):
                # Process message content blocks
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        # Add newline separator if coming after tool result
                        text = block.text
                        if last_block_type == 'tool_result':
                            text = "\n\n" + text

                        # Stream text content
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

                        # Tool call event
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
                        # Tool result event
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
                        if isinstance(block.content, dict):
                            if "preview_url" in block.content:
                                preview_url = block.content["preview_url"]
                            elif "url" in block.content:
                                preview_url = block.content["url"]

        # Send done event with preview URL if available
        done_event = {
            "type": "done",
            "preview_url": preview_url
        }
        if self.on_event:
            self.on_event(done_event)
        logger.info(f"[{self.session_id}] Chat completed, preview_url={preview_url}")
        yield done_event

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

            # Cleanup sandbox manager (will close any active sandboxes)
            if self.sandbox_manager:
                await self.sandbox_manager.destroy()
                self.sandbox_manager = None
                logger.debug(f"[{self.session_id}] Sandbox manager destroyed")

            # Close MCP server
            if self.mcp_server:
                # MCP server cleanup (if it has a close method)
                if hasattr(self.mcp_server, 'close'):
                    await self.mcp_server.close()
                self.mcp_server = None
                logger.debug(f"[{self.session_id}] MCP server closed")

            self._initialized = False
            logger.info(f"[{self.session_id}] Agent cleanup completed")

        except Exception as e:
            logger.error(f"[{self.session_id}] Error during cleanup: {e}", exc_info=True)
