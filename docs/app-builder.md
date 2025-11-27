# App Builder - "Lovable for Data"

> AI-powered app builder pro datové aplikace s live preview v E2B sandboxu

## Obsah

1. [Vize projektu](#vize-projektu)
2. [Analýza E2B Fragments](#analýza-e2b-fragments)
3. [Architektura](#architektura)
4. [Technologie](#technologie)
5. [Implementační plán](#implementační-plán)
6. [API Reference](#api-reference)
7. [Claude Agent SDK](#claude-agent-sdk)

---

## Vize projektu

### Co chceme vytvořit

**App Builder** - systém, kde uživatel může:
1. V levém panelu **chatovat s AI** o tom, co chce vytvořit
2. V pravém panelu **vidět živou aplikaci** běžící v E2B sandboxu
3. Iterativně **vylepšovat aplikaci** přirozeným jazykem

### Klíčové principy

- **React/TypeScript/Next.js** - ne Streamlit, moderní frontend stack
- **Claude Agent SDK** - pro inteligentní generování a editaci kódu
- **E2B Sandbox** - izolované prostředí s hot-reload
- **Multi-file projekty** - ne jen jeden soubor, ale celé aplikace
- **Iterativní vývoj** - AI si pamatuje kontext a může opravovat chyby

---

## Analýza E2B Fragments

> Repozitář: https://github.com/e2b-dev/fragments

### Struktura projektu

```
e2b-fragments/
├── app/
│   ├── api/
│   │   ├── chat/route.ts      # AI chat endpoint
│   │   ├── sandbox/route.ts   # E2B sandbox creation
│   │   └── morph-chat/route.ts # Edit mode endpoint
│   ├── page.tsx               # Hlavní stránka
│   └── layout.tsx
├── components/
│   ├── chat.tsx               # Chat komponenta
│   ├── chat-input.tsx         # Input s file upload
│   ├── preview.tsx            # Preview panel
│   ├── code-view.tsx          # Monaco editor
│   └── ui/                    # shadcn komponenty
├── lib/
│   ├── schema.ts              # Zod schema pro fragment
│   ├── prompt.ts              # System prompt
│   ├── templates.ts           # E2B templates definice
│   └── models.ts              # LLM konfigurace
└── sandbox-templates/         # E2B template definice
```

### Jak Fragments funguje

#### 1. Chat API (`/api/chat/route.ts`)

```typescript
// Používá Vercel AI SDK s streamObject
import { streamObject } from 'ai'
import { fragmentSchema } from '@/lib/schema'

const stream = await streamObject({
  model: modelClient,
  schema: fragmentSchema,  // Zod schema
  system: toPrompt(template),
  messages,
})

return stream.toTextStreamResponse()
```

#### 2. Fragment Schema (`lib/schema.ts`)

```typescript
export const fragmentSchema = z.object({
  commentary: z.string().describe('Popis co se děje'),
  template: z.string().describe('Název E2B template'),
  title: z.string().describe('Krátký název'),
  description: z.string().describe('Popis'),
  additional_dependencies: z.array(z.string()),
  has_additional_dependencies: z.boolean(),
  install_dependencies_command: z.string(),
  port: z.number().nullable(),
  file_path: z.string().describe('Cesta k souboru'),
  code: z.string().describe('Vygenerovaný kód'),
})
```

#### 3. Sandbox API (`/api/sandbox/route.ts`)

```typescript
import { Sandbox } from '@e2b/code-interpreter'

// Vytvoření sandboxu
const sbx = await Sandbox.create(fragment.template, {
  metadata: { template, userID, teamID },
  timeoutMs: 10 * 60 * 1000, // 10 minut
})

// Instalace dependencies
if (fragment.has_additional_dependencies) {
  await sbx.commands.run(fragment.install_dependencies_command)
}

// Zápis kódu do sandboxu
await sbx.files.write(fragment.file_path, fragment.code)

// Vrácení URL
return {
  sbxId: sbx.sandboxId,
  url: `https://${sbx.getHost(fragment.port)}`,
}
```

#### 4. Templates (`lib/templates.ts`)

```typescript
const templates = {
  'nextjs-developer': {
    name: 'Next.js developer',
    lib: ['nextjs@14.2.5', 'typescript', 'tailwindcss', 'shadcn'],
    file: 'pages/index.tsx',
    instructions: 'A Next.js 13+ app that reloads automatically.',
    port: 3000,
  },
  'streamlit-developer': {
    name: 'Streamlit developer',
    lib: ['streamlit', 'pandas', 'plotly'],
    file: 'app.py',
    port: 8501,
  },
  // ...
}
```

#### 5. Frontend Flow (`app/page.tsx`)

```typescript
// Vercel AI SDK hook
const { object, submit, isLoading, stop } = useObject({
  api: '/api/chat',
  schema: fragmentSchema,
  onFinish: async ({ object: fragment }) => {
    // Po dokončení generování → vytvoř sandbox
    const response = await fetch('/api/sandbox', {
      method: 'POST',
      body: JSON.stringify({ fragment }),
    })
    const result = await response.json()
    setResult(result) // URL pro preview
  },
})

// Submit zprávy
submit({
  messages: toAISDKMessages(messages),
  template: currentTemplate,
  model: currentModel,
})
```

### Omezení Fragments přístupu

| Limitace | Problém |
|----------|---------|
| Single-file | Generuje pouze jeden soubor najednou |
| Schema-bound | Rigidní struktura výstupu |
| No error recovery | Nemůže reagovat na runtime chyby |
| No iteration | Každá změna = nový fragment |
| Limited context | Nepamatuje si předchozí soubory |

---

## Architektura

### High-level diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js 14)                            │
├──────────────────────────────┬─────────────────────────────────────────┤
│       Chat Panel             │           Preview Panel                  │
│  ┌────────────────────────┐  │  ┌───────────────────────────────────┐  │
│  │ • Message list         │  │  │ • Live iframe (E2B URL)          │  │
│  │ • Streaming responses  │  │  │ • Code tabs (Monaco)             │  │
│  │ • File attachments     │  │  │ • File tree                      │  │
│  │ • Progress indicators  │  │  │ • Console output                 │  │
│  │ • Tool use display     │  │  │ • Error display                  │  │
│  └────────────────────────┘  │  └───────────────────────────────────┘  │
└──────────────────────────────┴─────────────────────────────────────────┘
                                    │
                                    ▼ WebSocket (bidirectional streaming)
┌────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI + Python)                      │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│   WebSocket Handler (/ws/chat)                                         │
│   ├── Session management (conversation ID)                             │
│   ├── Message routing                                                  │
│   └── Event streaming to frontend                                      │
│                                                                        │
│   Claude Agent SDK (ClaudeSDKClient)                                   │
│   ├── Continuous conversation (maintains context)                      │
│   ├── System prompt (app builder instructions)                         │
│   ├── Permission mode: acceptEdits                                     │
│   │                                                                    │
│   ├── Custom MCP Tools (in-process):                                   │
│   │   ├── sandbox_create()          → vytvoří E2B sandbox             │
│   │   ├── sandbox_write_file()      → zapíše soubor do E2B            │
│   │   ├── sandbox_read_file()       → přečte soubor z E2B             │
│   │   ├── sandbox_run_command()     → spustí příkaz v E2B             │
│   │   ├── sandbox_install()         → npm/pip install v E2B           │
│   │   ├── sandbox_get_url()         → vrátí preview URL               │
│   │   └── sandbox_get_logs()        → vrátí console output            │
│   │                                                                    │
│   └── Hooks:                                                           │
│       ├── PreToolUse  → validace, logging                             │
│       └── PostToolUse → notify frontend, sync state                   │
│                                                                        │
│   E2B Sandbox Manager                                                  │
│   ├── Lazy initialization (vytvoří až při prvním tool use)            │
│   ├── Sandbox lifecycle (create, keep-alive, destroy)                 │
│   ├── File synchronization (track changes)                            │
│   └── URL management                                                   │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      E2B SANDBOX (Custom Template)                      │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  Base: Next.js 14 + TypeScript + Tailwind CSS                          │
│                                                                        │
│  Pre-installed packages:                                               │
│  ├── UI: shadcn/ui, lucide-react, framer-motion                       │
│  ├── Data viz: recharts, @tanstack/react-table, plotly.js             │
│  ├── Data: papaparse, xlsx, date-fns                                  │
│  └── State: zustand, @tanstack/react-query                            │
│                                                                        │
│  Project structure:                                                    │
│  ├── app/                    # Next.js app router                     │
│  │   ├── page.tsx            # Main page                              │
│  │   ├── layout.tsx          # Root layout                            │
│  │   └── api/                # API routes                             │
│  ├── components/             # React components                       │
│  │   └── ui/                 # shadcn components                      │
│  ├── lib/                    # Utilities                              │
│  └── public/                 # Static assets                          │
│                                                                        │
│  Hot-reload: Automatic on file changes                                 │
│  Port: 3000                                                            │
│  URL: https://{sandbox-id}-3000.e2b.dev                               │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### Proč Claude Agent SDK místo Vercel AI SDK?

| Aspekt | Vercel AI SDK (Fragments) | Claude Agent SDK (náš přístup) |
|--------|---------------------------|--------------------------------|
| **Output** | Strukturovaný (Zod schema) | Tool-based (flexibilní) |
| **Files** | Jeden soubor | Multi-file projekty |
| **Context** | Per-request | Persistent session |
| **Error handling** | Žádné | Může číst logy a opravit |
| **Iteration** | Nový fragment | Editace existujících souborů |
| **Complexity** | Jednoduché apps | Komplexní aplikace |
| **Control** | Omezené | Plná kontrola přes hooks |

### Data Flow

```
User Message
    │
    ▼
┌─────────────────┐
│ WebSocket       │
│ /ws/chat        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ClaudeSDKClient │
│ .query(message) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│ Claude thinks   │────▶│ Tool: write_file │
│ about request   │     └────────┬─────────┘
└─────────────────┘              │
                                 ▼
                    ┌──────────────────────┐
                    │ E2B Sandbox          │
                    │ sbx.files.write(...) │
                    └────────┬─────────────┘
                             │
                             ▼
                    ┌──────────────────────┐
                    │ PostToolUse Hook     │
                    │ → notify frontend    │
                    └────────┬─────────────┘
                             │
                             ▼
                    ┌──────────────────────┐
                    │ Frontend updates     │
                    │ • File tree          │
                    │ • Code view          │
                    │ • Preview refreshes  │
                    └──────────────────────┘
```

---

## Technologie

### Backend

| Technologie | Účel | Verze |
|-------------|------|-------|
| Python | Runtime | 3.11+ |
| FastAPI | Web framework | 0.115+ |
| claude-agent-sdk | AI agent | latest |
| e2b-code-interpreter | Sandbox | 1.0+ |
| websockets | Real-time komunikace | - |
| pydantic | Validace | 2.0+ |

### Frontend

| Technologie | Účel |
|-------------|------|
| Next.js 14 | Framework |
| TypeScript | Type safety |
| Tailwind CSS | Styling |
| shadcn/ui | UI komponenty |
| Monaco Editor | Code editing |
| Zustand | State management |
| Socket.io / native WS | Real-time |

### E2B Sandbox

| Technologie | Účel |
|-------------|------|
| Next.js 14 | App framework |
| TypeScript | Language |
| Tailwind CSS | Styling |
| shadcn/ui | UI components |
| recharts | Charts |
| @tanstack/react-table | Tables |
| plotly.js | Advanced viz |

---

## Implementační plán

### Fáze 1: Backend Foundation

**Cíl:** Funkční backend s Claude Agent SDK a E2B integrací

#### 1.1 Projekt setup
```bash
# Struktura
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── websocket.py         # WebSocket handlers
│   ├── sandbox_manager.py   # E2B sandbox lifecycle
│   ├── agent.py             # Claude Agent SDK wrapper
│   └── tools/
│       ├── __init__.py
│       └── sandbox_tools.py # MCP tools pro E2B
├── requirements.txt
└── .env
```

#### 1.2 Sandbox Manager

```python
# backend/app/sandbox_manager.py
from e2b_code_interpreter import Sandbox
from typing import Optional
import asyncio

class SandboxManager:
    def __init__(self):
        self.sandbox: Optional[Sandbox] = None
        self.sandbox_id: Optional[str] = None
        self.preview_url: Optional[str] = None

    async def ensure_sandbox(self, template: str = "nextjs-developer") -> Sandbox:
        """Lazy initialization - vytvoří sandbox až když je potřeba"""
        if self.sandbox is None:
            self.sandbox = await Sandbox.create(
                template,
                timeout_ms=15 * 60 * 1000,  # 15 minut
            )
            self.sandbox_id = self.sandbox.sandbox_id
            self.preview_url = f"https://{self.sandbox.get_host(3000)}"
        return self.sandbox

    async def write_file(self, path: str, content: str) -> dict:
        sbx = await self.ensure_sandbox()
        await sbx.files.write(path, content)
        return {"success": True, "path": path}

    async def read_file(self, path: str) -> str:
        sbx = await self.ensure_sandbox()
        return await sbx.files.read(path)

    async def run_command(self, command: str) -> dict:
        sbx = await self.ensure_sandbox()
        result = await sbx.commands.run(command)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
        }

    async def get_preview_url(self) -> str:
        await self.ensure_sandbox()
        return self.preview_url

    async def destroy(self):
        if self.sandbox:
            await self.sandbox.kill()
            self.sandbox = None
```

#### 1.3 MCP Tools

```python
# backend/app/tools/sandbox_tools.py
from claude_agent_sdk import tool, create_sdk_mcp_server
from typing import Any

# Reference na sandbox manager (injektuje se při vytvoření)
_sandbox_manager = None

def set_sandbox_manager(manager):
    global _sandbox_manager
    _sandbox_manager = manager

@tool(
    "sandbox_write_file",
    "Write or create a file in the sandbox. Use this to create new files or update existing ones.",
    {"file_path": str, "content": str}
)
async def sandbox_write_file(args: dict[str, Any]) -> dict[str, Any]:
    result = await _sandbox_manager.write_file(args["file_path"], args["content"])
    return {
        "content": [{
            "type": "text",
            "text": f"File written: {args['file_path']}"
        }]
    }

@tool(
    "sandbox_read_file",
    "Read contents of a file from the sandbox.",
    {"file_path": str}
)
async def sandbox_read_file(args: dict[str, Any]) -> dict[str, Any]:
    content = await _sandbox_manager.read_file(args["file_path"])
    return {
        "content": [{
            "type": "text",
            "text": content
        }]
    }

@tool(
    "sandbox_run_command",
    "Run a shell command in the sandbox. Use for npm install, running scripts, etc.",
    {"command": str}
)
async def sandbox_run_command(args: dict[str, Any]) -> dict[str, Any]:
    result = await _sandbox_manager.run_command(args["command"])
    output = result["stdout"] or result["stderr"] or "Command completed"
    return {
        "content": [{
            "type": "text",
            "text": f"Exit code: {result['exit_code']}\n{output}"
        }]
    }

@tool(
    "sandbox_get_preview_url",
    "Get the public URL for the sandbox preview. Call this after making changes to show the user.",
    {}
)
async def sandbox_get_preview_url(args: dict[str, Any]) -> dict[str, Any]:
    url = await _sandbox_manager.get_preview_url()
    return {
        "content": [{
            "type": "text",
            "text": f"Preview URL: {url}"
        }]
    }

@tool(
    "sandbox_list_files",
    "List files in a directory in the sandbox.",
    {"path": str}
)
async def sandbox_list_files(args: dict[str, Any]) -> dict[str, Any]:
    result = await _sandbox_manager.run_command(f"find {args['path']} -type f -name '*.tsx' -o -name '*.ts' -o -name '*.css' 2>/dev/null | head -50")
    return {
        "content": [{
            "type": "text",
            "text": result["stdout"] or "No files found"
        }]
    }

# Vytvoření MCP serveru
def create_sandbox_tools_server(sandbox_manager):
    set_sandbox_manager(sandbox_manager)
    return create_sdk_mcp_server(
        name="sandbox",
        version="1.0.0",
        tools=[
            sandbox_write_file,
            sandbox_read_file,
            sandbox_run_command,
            sandbox_get_preview_url,
            sandbox_list_files,
        ]
    )
```

#### 1.4 Agent Wrapper

```python
# backend/app/agent.py
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock, ToolUseBlock
from .sandbox_manager import SandboxManager
from .tools.sandbox_tools import create_sandbox_tools_server
from typing import AsyncIterator, Callable
import asyncio

SYSTEM_PROMPT = """You are an expert React/Next.js developer building data applications.

You have access to an E2B sandbox where you can create and modify files. The sandbox runs Next.js 14 with:
- TypeScript
- Tailwind CSS
- shadcn/ui components
- recharts for charts
- @tanstack/react-table for tables

WORKFLOW:
1. When user asks for an app, first plan the file structure
2. Create files one by one using sandbox_write_file
3. After creating/modifying files, call sandbox_get_preview_url to show the result
4. If there are errors, read the file and fix them

FILE STRUCTURE:
- app/page.tsx - Main page
- app/layout.tsx - Root layout (already exists)
- components/ - React components
- lib/ - Utilities

IMPORTANT:
- Always use TypeScript
- Use shadcn/ui components when possible
- Make the UI beautiful with Tailwind
- Handle loading and error states
- Use 'use client' directive for interactive components
"""

class AppBuilderAgent:
    def __init__(self, on_event: Callable = None):
        self.sandbox_manager = SandboxManager()
        self.client: ClaudeSDKClient = None
        self.on_event = on_event  # Callback pro frontend notifikace

    async def initialize(self):
        """Inicializace agenta s MCP tools"""
        sandbox_server = create_sandbox_tools_server(self.sandbox_manager)

        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            mcp_servers={"sandbox": sandbox_server},
            allowed_tools=[
                "mcp__sandbox__sandbox_write_file",
                "mcp__sandbox__sandbox_read_file",
                "mcp__sandbox__sandbox_run_command",
                "mcp__sandbox__sandbox_get_preview_url",
                "mcp__sandbox__sandbox_list_files",
            ],
            permission_mode="acceptEdits",
        )

        self.client = ClaudeSDKClient(options)
        await self.client.connect()

    async def chat(self, message: str) -> AsyncIterator[dict]:
        """Zpracování zprávy od uživatele"""
        await self.client.query(message)

        async for msg in self.client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        yield {"type": "text", "content": block.text}
                    elif isinstance(block, ToolUseBlock):
                        yield {
                            "type": "tool_use",
                            "tool": block.name,
                            "input": block.input,
                        }
            elif hasattr(msg, 'subtype') and msg.subtype in ['success', 'error']:
                yield {
                    "type": "done",
                    "preview_url": self.sandbox_manager.preview_url,
                }
                break

    async def cleanup(self):
        """Cleanup resources"""
        if self.client:
            await self.client.disconnect()
        await self.sandbox_manager.destroy()
```

#### 1.5 WebSocket Handler

```python
# backend/app/websocket.py
from fastapi import WebSocket, WebSocketDisconnect
from .agent import AppBuilderAgent
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.agents: dict[str, AppBuilderAgent] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

        # Vytvoř agenta pro tuto session
        agent = AppBuilderAgent()
        await agent.initialize()
        self.agents[session_id] = agent

    async def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.agents:
            await self.agents[session_id].cleanup()
            del self.agents[session_id]

    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)

    async def handle_message(self, session_id: str, data: dict):
        agent = self.agents.get(session_id)
        if not agent:
            return

        user_message = data.get("message", "")

        # Stream odpovědí od agenta
        async for event in agent.chat(user_message):
            await self.send_message(session_id, event)

manager = ConnectionManager()
```

#### 1.6 FastAPI Main

```python
# backend/app/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from .websocket import manager
import uuid

app = FastAPI(title="App Builder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/chat/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.handle_message(session_id, data)
    except WebSocketDisconnect:
        await manager.disconnect(session_id)

@app.post("/api/session")
async def create_session():
    """Vytvoří novou session"""
    session_id = str(uuid.uuid4())
    return {"session_id": session_id}

@app.get("/health")
async def health():
    return {"status": "ok"}
```

### Fáze 2: E2B Template

**Cíl:** Custom Next.js template optimalizovaný pro data apps

#### 2.1 Template struktura

```bash
sandbox-template/
├── e2b.toml                 # E2B konfigurace
├── package.json
├── next.config.mjs
├── tailwind.config.ts
├── tsconfig.json
├── app/
│   ├── layout.tsx           # Root layout s providers
│   ├── page.tsx             # Placeholder
│   └── globals.css          # Tailwind + custom styles
├── components/
│   └── ui/                  # shadcn komponenty
│       ├── button.tsx
│       ├── card.tsx
│       ├── input.tsx
│       ├── table.tsx
│       └── ...
└── lib/
    └── utils.ts             # cn() helper
```

#### 2.2 e2b.toml

```toml
# e2b.toml
template_id = "nextjs-data-app"
dockerfile = "Dockerfile"
start_cmd = "npm run dev"
```

#### 2.3 Package.json

```json
{
  "name": "data-app-template",
  "version": "1.0.0",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "14.2.5",
    "react": "^18",
    "react-dom": "^18",
    "typescript": "^5",

    "tailwindcss": "^3.4",
    "class-variance-authority": "^0.7",
    "clsx": "^2.1",
    "tailwind-merge": "^2.3",

    "@radix-ui/react-dialog": "^1.0",
    "@radix-ui/react-dropdown-menu": "^2.0",
    "@radix-ui/react-select": "^2.0",
    "@radix-ui/react-tabs": "^1.0",
    "@radix-ui/react-tooltip": "^1.0",

    "recharts": "^2.12",
    "@tanstack/react-table": "^8.17",
    "plotly.js": "^2.33",
    "react-plotly.js": "^2.6",

    "papaparse": "^5.4",
    "xlsx": "^0.18",
    "date-fns": "^3.6",

    "lucide-react": "^0.378",
    "framer-motion": "^11.2",
    "zustand": "^4.5",
    "@tanstack/react-query": "^5.40"
  },
  "devDependencies": {
    "@types/node": "^20",
    "@types/react": "^18",
    "@types/react-dom": "^18",
    "autoprefixer": "^10",
    "postcss": "^8"
  }
}
```

### Fáze 3: Frontend

**Cíl:** Moderní chat + preview UI

#### 3.1 Projekt setup

```bash
npx create-next-app@latest app-builder-frontend \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --import-alias "@/*"
```

#### 3.2 Struktura

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx          # Main app
│   │   └── globals.css
│   ├── components/
│   │   ├── chat/
│   │   │   ├── ChatPanel.tsx
│   │   │   ├── MessageList.tsx
│   │   │   ├── ChatInput.tsx
│   │   │   └── ToolUseDisplay.tsx
│   │   ├── preview/
│   │   │   ├── PreviewPanel.tsx
│   │   │   ├── CodeView.tsx
│   │   │   ├── FileTree.tsx
│   │   │   └── ConsoleOutput.tsx
│   │   └── ui/               # shadcn
│   ├── lib/
│   │   ├── websocket.ts      # WS client
│   │   └── store.ts          # Zustand store
│   └── types/
│       └── index.ts
├── package.json
└── tailwind.config.ts
```

#### 3.3 WebSocket Client

```typescript
// src/lib/websocket.ts
type MessageHandler = (data: any) => void;

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private sessionId: string;
  private handlers: MessageHandler[] = [];

  constructor(sessionId: string) {
    this.sessionId = sessionId;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(`ws://localhost:8000/ws/chat/${this.sessionId}`);

      this.ws.onopen = () => resolve();
      this.ws.onerror = (e) => reject(e);
      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        this.handlers.forEach(h => h(data));
      };
    });
  }

  send(message: string) {
    this.ws?.send(JSON.stringify({ message }));
  }

  onMessage(handler: MessageHandler) {
    this.handlers.push(handler);
    return () => {
      this.handlers = this.handlers.filter(h => h !== handler);
    };
  }

  disconnect() {
    this.ws?.close();
  }
}
```

#### 3.4 Zustand Store

```typescript
// src/lib/store.ts
import { create } from 'zustand';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  toolUse?: {
    tool: string;
    input: any;
  };
}

interface AppState {
  sessionId: string | null;
  messages: Message[];
  previewUrl: string | null;
  isLoading: boolean;
  files: string[];

  setSessionId: (id: string) => void;
  addMessage: (message: Message) => void;
  updateLastMessage: (content: string) => void;
  setPreviewUrl: (url: string) => void;
  setLoading: (loading: boolean) => void;
  setFiles: (files: string[]) => void;
  reset: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  sessionId: null,
  messages: [],
  previewUrl: null,
  isLoading: false,
  files: [],

  setSessionId: (id) => set({ sessionId: id }),
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),
  updateLastMessage: (content) => set((state) => ({
    messages: state.messages.map((m, i) =>
      i === state.messages.length - 1
        ? { ...m, content: m.content + content }
        : m
    )
  })),
  setPreviewUrl: (url) => set({ previewUrl: url }),
  setLoading: (loading) => set({ isLoading: loading }),
  setFiles: (files) => set({ files }),
  reset: () => set({
    messages: [],
    previewUrl: null,
    isLoading: false,
    files: []
  }),
}));
```

#### 3.5 Main Page

```typescript
// src/app/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { ChatPanel } from '@/components/chat/ChatPanel';
import { PreviewPanel } from '@/components/preview/PreviewPanel';
import { WebSocketClient } from '@/lib/websocket';
import { useAppStore } from '@/lib/store';
import { v4 as uuid } from 'uuid';

export default function Home() {
  const [ws, setWs] = useState<WebSocketClient | null>(null);
  const {
    sessionId,
    setSessionId,
    addMessage,
    updateLastMessage,
    setPreviewUrl,
    setLoading,
    previewUrl
  } = useAppStore();

  useEffect(() => {
    // Initialize session
    const id = uuid();
    setSessionId(id);

    const client = new WebSocketClient(id);
    client.connect().then(() => {
      setWs(client);

      client.onMessage((data) => {
        switch (data.type) {
          case 'text':
            updateLastMessage(data.content);
            break;
          case 'tool_use':
            // Display tool usage
            break;
          case 'done':
            setLoading(false);
            if (data.preview_url) {
              setPreviewUrl(data.preview_url);
            }
            break;
        }
      });
    });

    return () => client.disconnect();
  }, []);

  const handleSend = (message: string) => {
    if (!ws) return;

    addMessage({ id: uuid(), role: 'user', content: message });
    addMessage({ id: uuid(), role: 'assistant', content: '' });
    setLoading(true);
    ws.send(message);
  };

  return (
    <main className="flex h-screen">
      <div className="w-1/2 border-r">
        <ChatPanel onSend={handleSend} />
      </div>
      <div className="w-1/2">
        <PreviewPanel url={previewUrl} />
      </div>
    </main>
  );
}
```

### Fáze 4: Integration & Polish

**Cíl:** Propojení všech částí, error handling, UX

#### 4.1 Error Handling

```python
# backend/app/agent.py - rozšíření

async def chat(self, message: str) -> AsyncIterator[dict]:
    try:
        await self.client.query(message)
        async for msg in self.client.receive_response():
            # ... process messages
            pass
    except Exception as e:
        yield {
            "type": "error",
            "content": f"Error: {str(e)}"
        }
```

#### 4.2 File Tree Sync

```typescript
// Po každé změně souboru aktualizuj file tree
client.onMessage((data) => {
  if (data.type === 'tool_use' && data.tool === 'sandbox_write_file') {
    // Refresh file tree
    refreshFiles();
  }
});
```

#### 4.3 Console Output

```python
# Tool pro získání console output
@tool("sandbox_get_console", "Get recent console output from the sandbox", {})
async def sandbox_get_console(args):
    result = await _sandbox_manager.run_command("tail -50 /tmp/nextjs.log 2>/dev/null || echo 'No logs'")
    return {"content": [{"type": "text", "text": result["stdout"]}]}
```

---

## API Reference

### WebSocket Messages

#### Client → Server

```typescript
// Send chat message
{ "message": "Create a dashboard with a chart" }

// Request file list
{ "action": "list_files" }

// Stop current operation
{ "action": "stop" }
```

#### Server → Client

```typescript
// Text chunk (streaming)
{ "type": "text", "content": "I'll create..." }

// Tool use notification
{ "type": "tool_use", "tool": "sandbox_write_file", "input": { "file_path": "...", "content": "..." } }

// Tool result
{ "type": "tool_result", "tool": "sandbox_write_file", "result": { "success": true } }

// Done
{ "type": "done", "preview_url": "https://..." }

// Error
{ "type": "error", "content": "Error message" }

// Files update
{ "type": "files", "files": ["app/page.tsx", "components/Chart.tsx"] }
```

### REST Endpoints

```
POST /api/session
  → { "session_id": "uuid" }

GET /health
  → { "status": "ok" }
```

---

## Claude Agent SDK

### Klíčové koncepty

#### ClaudeSDKClient vs query()

| Feature | query() | ClaudeSDKClient |
|---------|---------|-----------------|
| Session | New each time | Persistent |
| Conversation | Single exchange | Multi-turn |
| Hooks | Not supported | Supported |
| Custom Tools | Not supported | Supported |
| Interrupts | Not supported | Supported |

**Pro náš use-case potřebujeme ClaudeSDKClient** protože:
- Chceme multi-turn konverzaci
- Potřebujeme custom MCP tools
- Chceme hooks pro notifikace

#### Custom MCP Tools

```python
from claude_agent_sdk import tool, create_sdk_mcp_server

@tool("name", "description", {"param1": str, "param2": int})
async def my_tool(args: dict) -> dict:
    # Tool implementation
    return {
        "content": [{
            "type": "text",
            "text": "Result"
        }]
    }

server = create_sdk_mcp_server(
    name="my_server",
    tools=[my_tool]
)
```

#### Hooks

```python
from claude_agent_sdk import ClaudeAgentOptions, HookMatcher

async def on_tool_use(input_data, tool_use_id, context):
    # Called before/after tool use
    return {}

options = ClaudeAgentOptions(
    hooks={
        'PreToolUse': [HookMatcher(hooks=[on_tool_use])],
        'PostToolUse': [HookMatcher(hooks=[on_tool_use])],
    }
)
```

#### Streaming Input

```python
async def message_generator():
    yield {"type": "text", "text": "First part"}
    await asyncio.sleep(1)
    yield {"type": "text", "text": "Second part"}

async with ClaudeSDKClient() as client:
    await client.query(message_generator())
    async for message in client.receive_response():
        print(message)
```

---

## Checklist

### Fáze 1: Backend ✅ DONE
- [x] Project setup (FastAPI, requirements.txt)
- [x] SandboxManager class
- [x] MCP Tools (write_file, read_file, run_command, get_url, install_packages, list_files)
- [x] AppBuilderAgent class with system prompt
- [x] WebSocket handler (ConnectionManager)
- [x] FastAPI main app (/ws/chat, /api/session, /health)
- [ ] Basic tests (skipped for MVP)

### Fáze 2: E2B Template ✅ DONE
- [x] e2b.toml configuration
- [x] Dockerfile for sandbox
- [x] package.json with all deps (Next.js, shadcn, recharts, etc.)
- [x] Base Next.js setup (app router, tailwind, typescript)
- [x] shadcn/ui Button component
- [ ] Template registration with E2B (requires `e2b template build`)

### Fáze 3: Frontend ✅ DONE
- [x] WebSocket client (lib/websocket.ts)
- [x] Zustand store (lib/store.ts)
- [x] Chat types (types/chat.ts)
- [x] ChatPanel component
- [x] ChatMessage component
- [x] ChatInput component
- [x] MessageList component
- [x] ToolUseIndicator component
- [x] PreviewPanel component
- [x] PreviewIframe component
- [x] CodeView component
- [x] ConsoleOutput component
- [x] FileTree component

### Fáze 4: Integration ⏳ TODO
- [ ] Create new App Builder page (frontend/src/AppBuilder.tsx)
  - Left panel: ChatPanel connected to WebSocket
  - Right panel: PreviewPanel showing E2B sandbox
- [ ] Wire up WebSocket connection in AppBuilder
  - Connect to backend ws://localhost:8000/ws/chat/{sessionId}
  - Handle all event types (text, tool_use, done, error)
- [ ] Update frontend routing (add /builder route or replace main app)
- [ ] Test end-to-end flow:
  1. Start backend: `cd backend && uvicorn app.main:app --reload`
  2. Start frontend: `cd frontend && npm run dev`
  3. Open http://localhost:5173
  4. Send message → Claude creates files → E2B sandbox runs → Preview shows app
- [ ] Build E2B template: `cd sandbox-template && e2b template build`
- [ ] Polish & error handling

---

## Poznámky a nápady

### Z Fragments repo

1. **Morph edit mode** - Fragments má speciální režim pro editace existujícího kódu (viz `morphEditSchema`)
2. **Multi-model support** - Podporuje různé LLM (Claude, GPT-4, Ollama)
3. **Rate limiting** - Implementováno pro veřejné použití
4. **Posthog analytics** - Tracking uživatelského chování

### Možná rozšíření

1. **Data upload** - Možnost nahrát CSV/Excel a použít v aplikaci
2. **Templates** - Předpřipravené šablony (dashboard, form, CRUD)
3. **Export** - Download vygenerovaného projektu jako ZIP
4. **Collaboration** - Sdílení session mezi uživateli
5. **Version history** - Git-like historie změn
6. **AI suggestions** - Návrhy na vylepšení

### Performance optimalizace

1. **Sandbox pooling** - Předvytvořené sandboxy pro rychlejší start
2. **File caching** - Cache přečtených souborů
3. **Incremental updates** - Posílat jen změny, ne celé soubory
4. **WebSocket reconnection** - Automatické znovupřipojení

---

*Poslední aktualizace: 2024-11-27*
