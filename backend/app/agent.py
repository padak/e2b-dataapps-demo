#!/usr/bin/env python3
"""
AppBuilderAgent - Claude Agent SDK wrapper for Next.js/React/TypeScript app builder.
Provides agentic workflow for building data applications in E2B sandboxes.
"""

import asyncio
from typing import AsyncIterator, Callable, Optional

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
)

from .sandbox_manager import SandboxManager
from .tools.sandbox_tools import create_sandbox_tools_server


SYSTEM_PROMPT = """You are an expert Next.js/React/TypeScript developer building data-driven web applications.

Your role is to help users build modern, production-quality web applications using:
- **Next.js 14+** with App Router
- **React 18+** with TypeScript
- **Tailwind CSS** for styling
- **shadcn/ui** for UI components
- **Data visualization** libraries (recharts, plotly, etc.)

## Your Capabilities

You have access to E2B sandbox tools that allow you to:
1. **Create files** - Write code files (components, pages, utilities, configs)
2. **Execute commands** - Run npm/yarn commands, build, test, install packages
3. **Read files** - Inspect existing code and configurations
4. **List files** - Explore project structure
5. **Install packages** - Add npm dependencies
6. **Run dev server** - Start Next.js development server with hot reload
7. **Get preview URL** - Access the live running application

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

### 6. Testing & Validation

Before considering the app complete:
1. **Start dev server** - Verify the app runs without errors
2. **Check console** - No React warnings or errors
3. **Test responsiveness** - Works on mobile and desktop
4. **Validate data** - Data loads and displays correctly
5. **Check types** - TypeScript compiles without errors

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


class AppBuilderAgent:
    """
    AppBuilderAgent wraps Claude Agent SDK to provide agentic workflow
    for building Next.js/React/TypeScript applications in E2B sandboxes.
    """

    def __init__(self, on_event: Optional[Callable] = None):
        """
        Initialize the AppBuilderAgent.

        Args:
            on_event: Optional callback for frontend notifications.
                     Called with event dict: {"type": "...", ...}
        """
        self.on_event = on_event
        self.client: Optional[ClaudeSDKClient] = None
        self.sandbox_manager: Optional[SandboxManager] = None
        self.mcp_server = None
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize the Claude SDK client with MCP sandbox tools.
        Must be called before using chat().
        """
        if self._initialized:
            return

        # Initialize sandbox manager
        self.sandbox_manager = SandboxManager()

        # Create MCP tools server for sandbox operations
        self.mcp_server = create_sandbox_tools_server(self.sandbox_manager)

        # Configure Claude Agent SDK
        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
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
            ],
            # Accept edits automatically for faster workflow
            permission_mode="acceptEdits",
        )

        # Create and connect client
        self.client = ClaudeSDKClient(options)
        await self.client.connect()

        self._initialized = True

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
            raise RuntimeError(
                "AppBuilderAgent not initialized. Call initialize() first."
            )

        # Send message to Claude
        await self.client.query(message)

        # Track if we've started a dev server to get preview URL
        preview_url = None

        # Stream response from Claude
        async for msg in self.client.receive_response():
            if isinstance(msg, AssistantMessage):
                # Process message content blocks
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        # Stream text content
                        event = {
                            "type": "text",
                            "content": block.text
                        }
                        if self.on_event:
                            self.on_event(event)
                        yield event

                    elif isinstance(block, ToolUseBlock):
                        # Tool call event
                        event = {
                            "type": "tool_use",
                            "tool": block.name,
                            "input": block.input
                        }
                        if self.on_event:
                            self.on_event(event)
                        yield event

                        # Track if we got preview URL from start_dev_server
                        if block.name == "mcp__sandbox__start_dev_server":
                            # Will get URL from tool result
                            pass

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
        yield done_event

    async def cleanup(self) -> None:
        """
        Cleanup resources (close MCP server, cleanup sandboxes, etc.)
        Should be called when done using the agent.
        """
        try:
            # Disconnect Claude SDK client
            if self.client:
                await self.client.disconnect()
                self.client = None

            # Cleanup sandbox manager (will close any active sandboxes)
            if self.sandbox_manager:
                await self.sandbox_manager.destroy()
                self.sandbox_manager = None

            # Close MCP server
            if self.mcp_server:
                # MCP server cleanup (if it has a close method)
                if hasattr(self.mcp_server, 'close'):
                    await self.mcp_server.close()
                self.mcp_server = None

            self._initialized = False

        except Exception as e:
            # Log error but don't raise - cleanup should be best-effort
            print(f"Error during cleanup: {e}")
