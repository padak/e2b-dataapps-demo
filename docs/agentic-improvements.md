# Agentic Improvements - Využití plného potenciálu Claude Agent SDK

> Dokument popisující, jak transformovat náš App Builder z jednoduchého chatbota na robustní agentic systém využívající plnou sílu Claude Code.

## Obsah

1. [Executive Summary](#executive-summary)
2. [Srovnání: Náš Backend vs SDK vs Claude Code CLI](#srovnání-náš-backend-vs-sdk-vs-claude-code-cli)
3. [Co nám chybí](#co-nám-chybí)
4. [Architektura vylepšení](#architektura-vylepšení)
5. [Implementační plán](#implementační-plán)
6. [Konkrétní kód](#konkrétní-kód)
7. [Migrace](#migrace)

---

## Executive Summary

### Problém

Náš App Builder používá Claude Agent SDK jako "hloupý wrapper" - posíláme prompt a čekáme na odpověď. Nevyužíváme:
- Nativní nástroje Claude Code (Read, Write, Edit, Bash)
- Subagenty pro specializované úkoly
- Hooks pro validaci a self-correction
- Conversation memory pro multi-turn interakce
- Permission callbacks pro dynamickou kontrolu

### Řešení

Claude Agent SDK je **transport layer** ke Claude Code CLI. To znamená, že máme přístup ke **všem funkcím Claude Code** - nemusíme je reimplementovat jako custom MCP tools!

### Klíčové změny

| Současný stav | Nový přístup |
|---------------|--------------|
| Custom MCP tools pro file operace | Nativní `Read`, `Write`, `Edit`, `Bash` |
| Jeden monolitický agent | Specializovaní subagenti |
| Žádná validace výsledků | Hooks pro PostToolUse |
| Stateless (nová session každý request) | ClaudeSDKClient s memory |
| Hardcoded system prompt | Claude Code preset + append |

---

## Srovnání: Náš Backend vs SDK vs Claude Code CLI

### Tabulka funkcí

| Funkce | Náš Backend | SDK Capabilities | Claude Code CLI |
|--------|-------------|------------------|-----------------|
| **File Operations** | Custom MCP tools | Nativní tools ✅ | Nativní tools |
| **Code Editing** | `sandbox_write_file` (přepíše celý soubor) | `Edit` (surgical changes) ✅ | Edit s diff |
| **Shell Commands** | `sandbox_run_command` | `Bash` s background support ✅ | Bash s timeouts |
| **File Search** | `sandbox_list_files` (basic) | `Glob`, `Grep` ✅ | Glob, Grep s regex |
| **Subagents** | ❌ Nemáme | `agents` parameter ✅ | Task tool |
| **Hooks** | ❌ Nemáme | `PreToolUse`, `PostToolUse` ✅ | 9 hook types |
| **Conversation Memory** | ❌ Stateless | `ClaudeSDKClient` ✅ | Session management |
| **Permission Control** | ❌ Vše povoleno | `can_use_tool` callback ✅ | Permission modes |
| **System Prompt** | Hardcoded 287 řádků | Preset + append ✅ | CLAUDE.md |
| **Error Recovery** | ❌ Žádné | Hooks + subagents ✅ | Self-correction loops |
| **Cost Tracking** | Basic logging | `ResultMessage.total_cost_usd` ✅ | Built-in |

### Detailní srovnání nástrojů

#### File Operations

**Náš současný přístup:**
```python
@tool("sandbox_write_file", "Write file", {"file_path": str, "content": str})
async def sandbox_write_file(args):
    await sandbox.files.write(args["file_path"], args["content"])
    return {"content": [{"type": "text", "text": f"Written: {args['file_path']}"}]}
```

**Co SDK nabízí:**
```python
# Nativní tools - nemusíme nic definovat!
allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
```

**Výhody nativních tools:**
- `Edit` - chirurgické změny místo přepisu celého souboru
- `Glob` - pattern matching s `**/*.tsx`
- `Grep` - regex search s kontextem (`-A`, `-B`, `-C`)
- `Bash` - background processes, timeouts, process groups

#### Subagents

**Náš současný přístup:**
```python
# Jeden agent pro všechno
SYSTEM_PROMPT = """You are an expert React/Next.js developer..."""
# 287 řádků instrukcí pro jeden agent
```

**Co SDK nabízí:**
```python
agents = {
    "code-generator": AgentDefinition(
        description="Generates React/TypeScript code",
        prompt="You write clean, typed React code...",
        tools=["Write", "Read"],
        model="sonnet"
    ),
    "code-reviewer": AgentDefinition(
        description="Reviews code for errors and issues",
        prompt="You review code. Report only issues with confidence >= 80...",
        tools=["Read", "Grep", "Glob"],
        model="haiku"  # Levnější!
    ),
    "error-fixer": AgentDefinition(
        description="Fixes identified errors",
        prompt="You fix specific errors identified by reviewer...",
        tools=["Read", "Edit"],
        model="sonnet"
    ),
}
```

**Výhody subagentů:**
- Separace zodpovědností
- Různé modely pro různé úkoly (haiku pro review = levnější)
- Omezené nástroje per agent (security)
- Paralelní spouštění možné

#### Hooks

**Náš současný přístup:**
```python
# Žádné hooks - prostě spustíme tool a doufáme
async for msg in agent.chat(user_message):
    yield msg  # No validation
```

**Co SDK nabízí:**
```python
async def validate_build_result(input_data, tool_use_id, context):
    """PostToolUse hook - reaguje na výsledky nástrojů"""
    if input_data.get("tool_name") != "Bash":
        return {}

    response = input_data.get("tool_response", {})
    exit_code = response.get("exitCode", 0)
    output = response.get("output", "")

    if exit_code != 0:
        # Self-correction: přidej instrukce pro opravu
        return {
            "systemMessage": f"""
Build failed! Errors:
```
{output[:1000]}
```

REQUIRED ACTIONS:
1. Use the code-reviewer agent to analyze these errors
2. Use error-fixer agent to fix each issue
3. Run build again to verify
"""
        }
    return {}

hooks = {
    "PostToolUse": [
        HookMatcher(matcher="Bash", hooks=[validate_build_result])
    ]
}
```

**Výhody hooks:**
- Automatická detekce chyb
- Self-correction bez uživatelského zásahu
- Audit logging
- Permission validation

#### Conversation Memory

**Náš současný přístup:**
```python
# Každý request = nová session
async def handle_message(session_id, data):
    # Agent neví nic o předchozích zprávách
    async for event in agent.chat(data["message"]):
        await send(session_id, event)
```

**Co SDK nabízí:**
```python
# ClaudeSDKClient udržuje konverzaci
async with ClaudeSDKClient(options=options) as client:
    # První zpráva
    await client.query("Create a dashboard")
    async for msg in client.receive_response():
        yield msg

    # Follow-up - Claude VÍ o dashboardu
    await client.query("Add a chart to it")
    async for msg in client.receive_response():
        yield msg  # Claude ví, že "it" = dashboard
```

**Výhody:**
- Claude si pamatuje kontext
- Méně tokenů (nemusíme opakovat kontext)
- Přirozenější konverzace

---

## Co nám chybí

### 1. Self-Correction Loop

**Problém:** Když build selže, agent to neví a nedokáže se opravit.

**Řešení:**
```
User Request
    │
    ▼
┌─────────────────┐
│ Code Generator  │ ──────► Write files
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Build (npm run  │ ──────► PostToolUse Hook
│ build)          │              │
└────────┬────────┘              │
         │                       │
         ▼                       ▼
    Success?  ◄──────────── Check exit code
         │
    ┌────┴────┐
    │         │
   Yes        No
    │         │
    ▼         ▼
  Done    ┌─────────────────┐
          │ Code Reviewer   │ ──────► Analyze errors
          └────────┬────────┘
                   │
                   ▼
          ┌─────────────────┐
          │ Error Fixer     │ ──────► Fix issues
          └────────┬────────┘
                   │
                   ▼
              Build again (loop)
```

### 2. Specializovaní agenti

**Problém:** Jeden agent s 287 řádky promptu = nepřehledné, pomalé, drahé.

**Řešení:** Multi-agent architektura

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                        │
│  (Main agent - koordinuje ostatní)                          │
└─────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Code        │ │ Code        │ │ Error       │ │ Test        │
│ Generator   │ │ Reviewer    │ │ Fixer       │ │ Runner      │
│             │ │             │ │             │ │             │
│ Model:      │ │ Model:      │ │ Model:      │ │ Model:      │
│ sonnet      │ │ haiku       │ │ sonnet      │ │ haiku       │
│             │ │             │ │             │ │             │
│ Tools:      │ │ Tools:      │ │ Tools:      │ │ Tools:      │
│ Write,Read  │ │ Read,Grep   │ │ Read,Edit   │ │ Bash,Read   │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

### 3. Nativní nástroje místo MCP

**Problém:** Reimplementujeme nástroje, které už existují.

| Náš MCP Tool | Nativní alternativa | Výhody nativního |
|--------------|---------------------|------------------|
| `sandbox_write_file` | `Write` | Standardní, testovaný |
| `sandbox_read_file` | `Read` | Podporuje obrázky, PDF |
| `sandbox_run_command` | `Bash` | Background, timeout, signals |
| `sandbox_list_files` | `Glob` | Pattern matching |
| - | `Edit` | Surgical changes! |
| - | `Grep` | Regex s kontextem |

### 4. Permission Control

**Problém:** Vše je povoleno, žádná validace.

**Řešení:**
```python
async def validate_tool_use(tool_name: str, input_data: dict, context):
    """Dynamická kontrola permissions"""

    # Blokuj nebezpečné příkazy
    if tool_name == "Bash":
        command = input_data.get("command", "")
        dangerous = ["rm -rf /", "sudo", "> /dev/sda"]
        if any(d in command for d in dangerous):
            return {
                "behavior": "deny",
                "message": "Dangerous command blocked"
            }

    # Omez file operace na sandbox
    if tool_name in ["Write", "Edit", "Read"]:
        path = input_data.get("file_path", "")
        if not path.startswith(f"/tmp/sandbox/{session_id}"):
            return {
                "behavior": "deny",
                "message": "Access outside sandbox denied"
            }

    return {"behavior": "allow"}
```

### 5. Cost Tracking

**Problém:** Nevíme kolik stojí jednotlivé operace.

**Řešení:**
```python
async for msg in client.receive_response():
    if isinstance(msg, ResultMessage):
        logger.info(f"Cost: ${msg.total_cost_usd:.4f}")
        logger.info(f"Tokens: {msg.usage}")
        logger.info(f"Duration: {msg.duration_ms}ms")
```

---

## Architektura vylepšení

### High-Level Design

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            FRONTEND                                      │
│  ┌─────────────────────┐      ┌─────────────────────────────────────┐   │
│  │ Chat Panel          │      │ Preview Panel                        │   │
│  │ - Message streaming │      │ - Live iframe                        │   │
│  │ - Tool use display  │      │ - Console output                     │   │
│  │ - Agent indicators  │      │ - File tree                          │   │
│  └─────────────────────┘      └─────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ WebSocket
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            BACKEND                                       │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    WebSocket Handler                             │    │
│  │  - Session management                                            │    │
│  │  - Message routing                                               │    │
│  │  - Event streaming                                               │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│                                    ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                 ClaudeSDKClient (Persistent)                     │    │
│  │                                                                  │    │
│  │  Options:                                                        │    │
│  │  ├── system_prompt: preset + append                             │    │
│  │  ├── allowed_tools: [Read, Write, Edit, Bash, Glob, Grep, Task] │    │
│  │  ├── agents: {code-reviewer, error-fixer, test-runner}          │    │
│  │  ├── hooks: {PostToolUse: [validate_build]}                     │    │
│  │  ├── mcp_servers: {e2b: [get_preview_url, start_server]}        │    │
│  │  ├── can_use_tool: permission_callback                          │    │
│  │  └── cwd: /tmp/sandbox/{session_id}                             │    │
│  │                                                                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
│                                    │ Spawns subprocess                   │
│                                    ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                      Claude Code CLI                             │    │
│  │                                                                  │    │
│  │  Native Tools:                                                   │    │
│  │  ├── Read    - Read files (text, images, PDF)                   │    │
│  │  ├── Write   - Create/overwrite files                           │    │
│  │  ├── Edit    - Surgical edits (old_string → new_string)         │    │
│  │  ├── Bash    - Shell commands with background support           │    │
│  │  ├── Glob    - File pattern matching                            │    │
│  │  ├── Grep    - Content search with regex                        │    │
│  │  └── Task    - Spawn subagents                                  │    │
│  │                                                                  │    │
│  │  Operates on: cwd = /tmp/sandbox/{session_id}                   │    │
│  │                                                                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                    │                                     │
└────────────────────────────────────│─────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         SANDBOX LAYER                                    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                   /tmp/sandbox/{session_id}/                     │    │
│  │                                                                  │    │
│  │  ├── app/                    # Next.js pages                    │    │
│  │  │   ├── page.tsx                                               │    │
│  │  │   ├── layout.tsx                                             │    │
│  │  │   └── globals.css                                            │    │
│  │  ├── components/             # React components                 │    │
│  │  ├── lib/                    # Utilities                        │    │
│  │  ├── package.json                                               │    │
│  │  └── next.config.js                                             │    │
│  │                                                                  │    │
│  │  Dev Server: npm run dev (background process)                   │    │
│  │  Port: 3000 + session_offset                                    │    │
│  │                                                                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  Pro produkci: E2B Sandbox (isolované, cloudové)                        │
│  Pro development: Local sandbox (rychlejší, jednodušší debug)           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Self-Correction Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        SELF-CORRECTION LOOP                               │
└──────────────────────────────────────────────────────────────────────────┘

User: "Create a dashboard with charts"
         │
         ▼
┌─────────────────────┐
│ 1. Generate Code    │
│    (main agent)     │
│                     │
│    Uses: Write      │
│    Creates files    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 2. Build Project    │
│    (main agent)     │
│                     │
│    Uses: Bash       │
│    npm run build    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 3. PostToolUse Hook │◄─────────────────────────────────────┐
│                     │                                       │
│    Checks exit code │                                       │
│    and output       │                                       │
└──────────┬──────────┘                                       │
           │                                                  │
           ▼                                                  │
      ┌────────────┐                                         │
      │ Success?   │                                         │
      └─────┬──────┘                                         │
            │                                                 │
       ┌────┴────┐                                           │
       │         │                                           │
      YES        NO                                          │
       │         │                                           │
       ▼         ▼                                           │
┌──────────┐ ┌─────────────────────┐                        │
│ 4. Done! │ │ 5. Code Reviewer    │                        │
│          │ │    (subagent)       │                        │
│ Start    │ │                     │                        │
│ preview  │ │    Uses: Read, Grep │                        │
│          │ │    Analyzes errors  │                        │
└──────────┘ └──────────┬──────────┘                        │
                        │                                    │
                        ▼                                    │
             ┌─────────────────────┐                        │
             │ 6. Error Fixer      │                        │
             │    (subagent)       │                        │
             │                     │                        │
             │    Uses: Read, Edit │                        │
             │    Fixes issues     │                        │
             └──────────┬──────────┘                        │
                        │                                    │
                        ▼                                    │
             ┌─────────────────────┐                        │
             │ 7. Rebuild          │                        │
             │    (main agent)     │────────────────────────┘
             │                     │
             │    Uses: Bash       │
             │    npm run build    │
             └─────────────────────┘
```

---

## Implementační plán

### Fáze 1: Přechod na nativní tools (1-2 hodiny)

**Cíl:** Nahradit custom MCP tools nativními nástroji Claude Code.

**Změny:**

1. **Upravit `ClaudeAgentOptions`:**
```python
# PŘED
options = ClaudeAgentOptions(
    mcp_servers={"sandbox": sandbox_server},
    allowed_tools=[
        "mcp__sandbox__sandbox_write_file",
        "mcp__sandbox__sandbox_read_file",
        "mcp__sandbox__sandbox_run_command",
        "mcp__sandbox__sandbox_list_files",
    ],
)

# PO
options = ClaudeAgentOptions(
    cwd=f"/tmp/sandbox/{session_id}",  # Klíčové! Nastaví working directory
    allowed_tools=[
        "Read", "Write", "Edit",  # File operations
        "Bash",                    # Shell commands
        "Glob", "Grep",            # Search
        "Task",                    # Subagents
        # Jen E2B-specifické jako MCP
        "mcp__e2b__get_preview_url",
        "mcp__e2b__start_dev_server",
    ],
    mcp_servers={"e2b": e2b_server},  # Zmenšený MCP server
)
```

2. **Zmenšit MCP server:**
```python
# Jen věci, které nativní tools neumí
@tool("get_preview_url", "Get live preview URL", {})
async def get_preview_url(args):
    url = f"http://localhost:{3000 + session_port_offset}"
    return {"content": [{"type": "text", "text": f"Preview: {url}"}]}

@tool("start_dev_server", "Start Next.js dev server", {})
async def start_dev_server(args):
    # Spuštění dev serveru na pozadí
    # (Bash to může taky, ale chceme trackovat port)
    ...

e2b_server = create_sdk_mcp_server(
    name="e2b",
    tools=[get_preview_url, start_dev_server]
)
```

3. **Upravit system prompt:**
```python
system_prompt = {
    "type": "preset",
    "preset": "claude_code",
    "append": """
## App Builder Context

You are building data apps in a sandbox at the current working directory.
The sandbox has Next.js 14 with TypeScript, Tailwind CSS, and shadcn/ui.

### Available Tools
- Read, Write, Edit: File operations (prefer Edit for changes)
- Bash: Run npm commands, start servers
- Glob, Grep: Search files and content
- Task: Delegate to specialized subagents

### Workflow
1. Create files using Write
2. Run `npm run build` to check for errors
3. If errors, analyze and fix them
4. Start dev server with start_dev_server tool
5. Get preview URL with get_preview_url tool
"""
}
```

### Fáze 2: Přidání subagentů (1-2 hodiny)

**Cíl:** Vytvořit specializované agenty pro různé úkoly.

```python
agents = {
    "code-reviewer": AgentDefinition(
        description="Reviews code for TypeScript/React errors. Use when build fails or you need code review.",
        prompt="""You are an expert TypeScript/React code reviewer.

## Your Task
Analyze error messages and source code to identify issues.

## Output Format
For each issue found, report:
```json
{
  "file": "path/to/file.tsx",
  "line": 42,
  "issue": "Brief description",
  "severity": "error|warning",
  "confidence": 85,
  "suggested_fix": "How to fix it"
}
```

## Rules
- Only report issues with confidence >= 80
- Focus on actual errors, not style preferences
- Be specific about line numbers and fixes
""",
        tools=["Read", "Grep", "Glob"],
        model="haiku"  # Levnější pro review
    ),

    "error-fixer": AgentDefinition(
        description="Fixes specific code errors identified by code-reviewer.",
        prompt="""You are a precise code fixer.

## Your Task
Fix the specific errors provided by code-reviewer.

## Rules
- Make minimal changes
- Use Edit tool for surgical fixes (not Write for whole file)
- Preserve existing code style
- Fix one issue at a time
- After fixing, briefly explain what you changed
""",
        tools=["Read", "Edit"],
        model="sonnet"
    ),

    "component-generator": AgentDefinition(
        description="Generates React components with TypeScript and Tailwind.",
        prompt="""You are a React component specialist.

## Your Task
Create clean, typed React components.

## Stack
- React 18 with hooks
- TypeScript (strict mode)
- Tailwind CSS for styling
- shadcn/ui for UI components

## Rules
- Use 'use client' for interactive components
- Export components as default
- Include proper TypeScript types
- Use semantic HTML
- Make responsive with Tailwind
""",
        tools=["Write", "Read"],
        model="sonnet"
    ),
}
```

### Fáze 3: Implementace hooks (1 hodina)

**Cíl:** Přidat self-correction pomocí hooks.

```python
async def validate_build_result(input_data, tool_use_id, context):
    """PostToolUse hook pro Bash - kontroluje výsledek buildu"""

    # Pouze pro Bash příkazy
    if input_data.get("tool_name") != "Bash":
        return {}

    command = input_data.get("tool_input", {}).get("command", "")
    response = input_data.get("tool_response", {})
    exit_code = response.get("exitCode", 0)
    output = response.get("output", "")

    # Kontrola build příkazů
    if "npm run build" in command or "npx tsc" in command:
        if exit_code != 0:
            # Build selhal - aktivuj self-correction
            return {
                "systemMessage": f"""
## Build Failed - Self-Correction Required

The build command failed with exit code {exit_code}.

### Error Output:
```
{output[:2000]}
```

### Required Actions:
1. Use the `code-reviewer` agent to analyze these errors
2. Use the `error-fixer` agent to fix each identified issue
3. Run the build again to verify fixes

Do NOT proceed to preview until build succeeds.
"""
            }
        else:
            # Build úspěšný
            return {
                "systemMessage": "Build successful! You can now start the dev server."
            }

    # Kontrola npm install
    if "npm install" in command and exit_code != 0:
        return {
            "systemMessage": f"""
npm install failed. Check package.json for issues:
```
{output[:1000]}
```
"""
        }

    return {}


async def log_tool_usage(input_data, tool_use_id, context):
    """PreToolUse hook - loguje všechny tool calls"""
    tool_name = input_data.get("tool_name", "unknown")
    tool_input = input_data.get("tool_input", {})

    logger.info(f"Tool: {tool_name}", extra={
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_use_id": tool_use_id,
    })

    return {}


async def validate_file_access(input_data, tool_use_id, context):
    """PreToolUse hook - validuje přístup k souborům"""
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if tool_name in ["Read", "Write", "Edit"]:
        file_path = tool_input.get("file_path", "")

        # Kontrola path traversal
        if ".." in file_path or file_path.startswith("/"):
            # Absolutní cesty mimo sandbox blokovat
            # (cwd je nastaven na sandbox, takže relativní cesty jsou OK)
            if not file_path.startswith(sandbox_path):
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": "Access outside sandbox denied"
                    }
                }

    return {}


# Konfigurace hooks
hooks = {
    "PreToolUse": [
        HookMatcher(hooks=[log_tool_usage]),
        HookMatcher(matcher="Read|Write|Edit", hooks=[validate_file_access]),
    ],
    "PostToolUse": [
        HookMatcher(matcher="Bash", hooks=[validate_build_result]),
    ],
}
```

### Fáze 4: ClaudeSDKClient s conversation memory (1 hodina)

**Cíl:** Přejít ze stateless na stateful konverzace.

```python
class SessionManager:
    """Spravuje ClaudeSDKClient instance pro jednotlivé sessions"""

    def __init__(self):
        self.clients: dict[str, ClaudeSDKClient] = {}
        self.options_factory = self._create_options

    def _create_options(self, session_id: str) -> ClaudeAgentOptions:
        """Vytvoří options pro novou session"""
        sandbox_path = f"/tmp/sandbox/{session_id}"

        return ClaudeAgentOptions(
            cwd=sandbox_path,
            system_prompt={
                "type": "preset",
                "preset": "claude_code",
                "append": SYSTEM_PROMPT_APPEND,
            },
            allowed_tools=[
                "Read", "Write", "Edit", "Bash", "Glob", "Grep", "Task",
                "mcp__e2b__get_preview_url",
                "mcp__e2b__start_dev_server",
            ],
            mcp_servers={"e2b": create_e2b_server(session_id)},
            agents=AGENTS,
            hooks=HOOKS,
            permission_mode="acceptEdits",
        )

    async def get_or_create_client(self, session_id: str) -> ClaudeSDKClient:
        """Vrátí existující nebo vytvoří nový client"""
        if session_id not in self.clients:
            options = self.options_factory(session_id)
            client = ClaudeSDKClient(options)
            await client.connect()
            self.clients[session_id] = client

        return self.clients[session_id]

    async def handle_message(self, session_id: str, message: str):
        """Zpracuje zprávu od uživatele"""
        client = await self.get_or_create_client(session_id)

        # Pošli zprávu - client si pamatuje předchozí kontext!
        await client.query(message)

        # Streamuj odpovědi
        async for msg in client.receive_response():
            yield self._format_message(msg)

    async def disconnect(self, session_id: str):
        """Odpojí a vyčistí session"""
        if session_id in self.clients:
            await self.clients[session_id].disconnect()
            del self.clients[session_id]
```

### Fáze 5: Permission callbacks (30 minut)

**Cíl:** Přidat dynamickou kontrolu permissions.

```python
async def permission_callback(
    tool_name: str,
    input_data: dict,
    context: dict
) -> dict:
    """Dynamická kontrola permissions pro tools"""

    # Bash commands - extra kontrola
    if tool_name == "Bash":
        command = input_data.get("command", "")

        # Blokované příkazy
        dangerous_patterns = [
            "rm -rf /",
            "rm -rf ~",
            "sudo ",
            "> /dev/",
            "mkfs",
            "dd if=",
            ":(){:|:&};:",  # Fork bomb
        ]

        for pattern in dangerous_patterns:
            if pattern in command:
                return {
                    "behavior": "deny",
                    "message": f"Dangerous command blocked: {pattern}"
                }

        # Varování pro potenciálně nebezpečné
        warning_patterns = ["rm -rf", "chmod 777", "curl | bash"]
        for pattern in warning_patterns:
            if pattern in command:
                logger.warning(f"Potentially dangerous command: {command}")

    # File operations - kontrola cesty
    if tool_name in ["Write", "Edit", "Read"]:
        file_path = input_data.get("file_path", "")

        # Sensitive files
        sensitive = [".env", "credentials", "secrets", ".git/config"]
        for s in sensitive:
            if s in file_path.lower():
                return {
                    "behavior": "deny",
                    "message": f"Access to sensitive file denied: {file_path}"
                }

    return {"behavior": "allow"}


# Přidání do options
options = ClaudeAgentOptions(
    can_use_tool=permission_callback,
    # ...
)
```

---

## Konkrétní kód

### Nový agent.py

```python
"""
App Builder Agent - využívá plnou sílu Claude Agent SDK
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, AsyncIterator

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AgentDefinition,
    HookMatcher,
    HookContext,
    tool,
    create_sdk_mcp_server,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    ResultMessage,
)

logger = logging.getLogger(__name__)


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

SYSTEM_PROMPT_APPEND = """
## App Builder Context

You are an AI assistant specialized in building data applications.
You work in a sandbox environment with Next.js 14, TypeScript, and Tailwind CSS.

### Your Capabilities

**Native Tools (prefer these):**
- `Read` - Read file contents
- `Write` - Create or overwrite files
- `Edit` - Make surgical changes to files (old_string → new_string)
- `Bash` - Run shell commands (npm, node, etc.)
- `Glob` - Find files by pattern
- `Grep` - Search file contents with regex
- `Task` - Delegate to specialized subagents

**Custom Tools:**
- `mcp__e2b__get_preview_url` - Get the live preview URL
- `mcp__e2b__start_dev_server` - Start the Next.js dev server

### Workflow

1. **Understand** - Clarify requirements if needed
2. **Plan** - Think about file structure
3. **Create** - Use Write to create files
4. **Verify** - Run `npm run build` to check for errors
5. **Fix** - If errors, use code-reviewer and error-fixer agents
6. **Preview** - Start dev server and provide preview URL

### Code Quality

- Always use TypeScript with proper types
- Use 'use client' for interactive components
- Follow React best practices (hooks, composition)
- Make UI responsive with Tailwind
- Handle loading and error states

### When Build Fails

If `npm run build` fails:
1. Use `Task` tool with `code-reviewer` agent to analyze errors
2. Use `Task` tool with `error-fixer` agent to fix issues
3. Rebuild and verify

Do NOT skip verification - always ensure build passes before preview.
"""


# =============================================================================
# SUBAGENTS
# =============================================================================

AGENTS = {
    "code-reviewer": AgentDefinition(
        description="Reviews TypeScript/React code for errors. Use when build fails.",
        prompt="""You are an expert code reviewer specializing in TypeScript and React.

## Task
Analyze error messages and find the root cause in source code.

## Process
1. Read the error message carefully
2. Use Grep to find the problematic code
3. Use Read to examine the full context
4. Identify the exact issue

## Output Format
Return a JSON array of issues:
```json
[
  {
    "file": "app/page.tsx",
    "line": 42,
    "issue": "Missing import for useState",
    "confidence": 95,
    "fix": "Add: import { useState } from 'react'"
  }
]
```

## Rules
- Only report issues with confidence >= 80
- Be specific about file paths and line numbers
- Suggest concrete fixes
""",
        tools=["Read", "Grep", "Glob"],
        model="haiku"
    ),

    "error-fixer": AgentDefinition(
        description="Fixes code errors identified by code-reviewer.",
        prompt="""You are a precise code fixer.

## Task
Apply specific fixes to code based on reviewer feedback.

## Process
1. Read the current file content
2. Use Edit to make surgical changes
3. Verify the change makes sense

## Rules
- Use Edit tool, not Write (preserves more context)
- Make minimal changes
- One fix at a time
- Preserve code style
""",
        tools=["Read", "Edit"],
        model="sonnet"
    ),

    "component-generator": AgentDefinition(
        description="Generates React components. Use for creating new UI components.",
        prompt="""You are a React component specialist.

## Stack
- React 18 with hooks
- TypeScript strict mode
- Tailwind CSS
- shadcn/ui components

## Rules
- Use 'use client' for components with state/effects
- Export as default
- Include proper types
- Make responsive
- Use semantic HTML
""",
        tools=["Write", "Read"],
        model="sonnet"
    ),
}


# =============================================================================
# HOOKS
# =============================================================================

async def validate_build_result(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: HookContext
) -> dict[str, Any]:
    """PostToolUse hook - validates build results and triggers self-correction"""

    if input_data.get("tool_name") != "Bash":
        return {}

    command = input_data.get("tool_input", {}).get("command", "")
    response = input_data.get("tool_response", {})
    exit_code = response.get("exitCode", 0)
    output = response.get("output", "")

    # Check build commands
    if any(cmd in command for cmd in ["npm run build", "npx tsc", "next build"]):
        if exit_code != 0:
            return {
                "systemMessage": f"""
## Build Failed - Self-Correction Required

Exit code: {exit_code}

### Errors:
```
{output[:2000]}
```

### Required Actions:
1. Use Task tool with `code-reviewer` agent to analyze errors
2. Use Task tool with `error-fixer` agent to fix issues
3. Run build again

Do NOT proceed until build succeeds.
"""
            }

    return {}


async def log_tool_usage(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: HookContext
) -> dict[str, Any]:
    """PreToolUse hook - logs all tool calls"""

    tool_name = input_data.get("tool_name", "unknown")
    tool_input = input_data.get("tool_input", {})

    logger.info(f"Tool call: {tool_name}", extra={
        "tool_name": tool_name,
        "tool_use_id": tool_use_id,
    })

    return {}


HOOKS = {
    "PreToolUse": [
        HookMatcher(hooks=[log_tool_usage]),
    ],
    "PostToolUse": [
        HookMatcher(matcher="Bash", hooks=[validate_build_result]),
    ],
}


# =============================================================================
# E2B MCP SERVER (jen E2B-specifické tools)
# =============================================================================

def create_e2b_server(session_id: str, port_offset: int = 0):
    """Vytvoří MCP server pro E2B-specifické operace"""

    base_port = 3000 + port_offset

    @tool("get_preview_url", "Get the live preview URL for the app", {})
    async def get_preview_url(args: dict[str, Any]) -> dict[str, Any]:
        url = f"http://localhost:{base_port}"
        return {
            "content": [{
                "type": "text",
                "text": f"Preview URL: {url}\n\nOpen this URL in the preview panel to see your app."
            }]
        }

    @tool("start_dev_server", "Start the Next.js development server", {})
    async def start_dev_server(args: dict[str, Any]) -> dict[str, Any]:
        # Dev server se spouští přes Bash tool s background=True
        # Tento tool jen vrací instrukce
        return {
            "content": [{
                "type": "text",
                "text": f"""To start the dev server, run:
```bash
npm run dev -- --port {base_port}
```

Use the Bash tool with this command.
After starting, use get_preview_url to get the preview link.
"""
            }]
        }

    return create_sdk_mcp_server(
        name="e2b",
        version="1.0.0",
        tools=[get_preview_url, start_dev_server]
    )


# =============================================================================
# PERMISSION CALLBACK
# =============================================================================

async def permission_callback(
    tool_name: str,
    input_data: dict,
    context: dict
) -> dict:
    """Validates tool usage dynamically"""

    if tool_name == "Bash":
        command = input_data.get("command", "")

        # Block dangerous commands
        dangerous = ["rm -rf /", "sudo ", "> /dev/", "mkfs", ":(){:|:&};:"]
        for pattern in dangerous:
            if pattern in command:
                logger.warning(f"Blocked dangerous command: {command}")
                return {
                    "behavior": "deny",
                    "message": f"Dangerous command blocked"
                }

    return {"behavior": "allow"}


# =============================================================================
# APP BUILDER AGENT
# =============================================================================

class AppBuilderAgent:
    """
    App Builder agent using full Claude Agent SDK capabilities.

    Features:
    - Native tools (Read, Write, Edit, Bash, Glob, Grep, Task)
    - Specialized subagents for code review and error fixing
    - Self-correction via PostToolUse hooks
    - Conversation memory via ClaudeSDKClient
    """

    def __init__(self, session_id: str, sandbox_path: str | Path):
        self.session_id = session_id
        self.sandbox_path = Path(sandbox_path)
        self.client: ClaudeSDKClient | None = None
        self.port_offset = hash(session_id) % 1000  # Unique port per session

    def _create_options(self) -> ClaudeAgentOptions:
        """Create SDK options with all features enabled"""

        return ClaudeAgentOptions(
            # Working directory = sandbox
            cwd=str(self.sandbox_path),

            # System prompt using Claude Code preset + our additions
            system_prompt={
                "type": "preset",
                "preset": "claude_code",
                "append": SYSTEM_PROMPT_APPEND,
            },

            # Native tools + E2B MCP tools
            allowed_tools=[
                # Native Claude Code tools
                "Read", "Write", "Edit",
                "Bash",
                "Glob", "Grep",
                "Task",  # For subagents
                # E2B specific
                "mcp__e2b__get_preview_url",
                "mcp__e2b__start_dev_server",
            ],

            # E2B MCP server
            mcp_servers={
                "e2b": create_e2b_server(self.session_id, self.port_offset)
            },

            # Specialized subagents
            agents=AGENTS,

            # Hooks for self-correction
            hooks=HOOKS,

            # Permission callback
            can_use_tool=permission_callback,

            # Auto-accept file edits
            permission_mode="acceptEdits",
        )

    async def initialize(self):
        """Initialize the agent and connect"""

        # Ensure sandbox exists
        self.sandbox_path.mkdir(parents=True, exist_ok=True)

        # Create client with options
        options = self._create_options()
        self.client = ClaudeSDKClient(options)
        await self.client.connect()

        logger.info(f"Agent initialized for session {self.session_id}")

    async def chat(self, message: str) -> AsyncIterator[dict[str, Any]]:
        """
        Process a user message and stream responses.

        The client maintains conversation history, so follow-up
        messages will have full context.
        """

        if not self.client:
            raise RuntimeError("Agent not initialized")

        # Send message to Claude
        await self.client.query(message)

        # Stream responses
        async for msg in self.client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        yield {
                            "type": "text",
                            "content": block.text,
                        }
                    elif isinstance(block, ToolUseBlock):
                        yield {
                            "type": "tool_use",
                            "tool": block.name,
                            "input": block.input,
                            "id": block.id,
                        }
                    elif isinstance(block, ToolResultBlock):
                        yield {
                            "type": "tool_result",
                            "tool_use_id": block.tool_use_id,
                            "content": block.content,
                            "is_error": block.is_error,
                        }

            elif isinstance(msg, ResultMessage):
                yield {
                    "type": "done",
                    "session_id": msg.session_id,
                    "cost_usd": msg.total_cost_usd,
                    "duration_ms": msg.duration_ms,
                    "num_turns": msg.num_turns,
                    "is_error": msg.is_error,
                }

    async def cleanup(self):
        """Disconnect and cleanup"""
        if self.client:
            await self.client.disconnect()
            self.client = None

        logger.info(f"Agent cleaned up for session {self.session_id}")
```

### Nový websocket.py

```python
"""
WebSocket handler with session-scoped ClaudeSDKClient instances
"""

import asyncio
import logging
from fastapi import WebSocket, WebSocketDisconnect
from pathlib import Path

from .agent import AppBuilderAgent

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and their associated agents"""

    def __init__(self, sandbox_base_path: str = "/tmp/sandbox"):
        self.connections: dict[str, WebSocket] = {}
        self.agents: dict[str, AppBuilderAgent] = {}
        self.sandbox_base = Path(sandbox_base_path)
        self._locks: dict[str, asyncio.Lock] = {}

    def _get_lock(self, session_id: str) -> asyncio.Lock:
        """Get or create lock for session"""
        if session_id not in self._locks:
            self._locks[session_id] = asyncio.Lock()
        return self._locks[session_id]

    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept connection and initialize agent"""
        await websocket.accept()
        self.connections[session_id] = websocket

        # Create agent with sandbox path
        sandbox_path = self.sandbox_base / session_id
        agent = AppBuilderAgent(session_id, sandbox_path)

        try:
            await agent.initialize()
            self.agents[session_id] = agent
            logger.info(f"Session {session_id} connected and initialized")
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            await websocket.close(code=1011, reason=str(e))
            raise

    async def disconnect(self, session_id: str):
        """Cleanup connection and agent"""
        if session_id in self.connections:
            del self.connections[session_id]

        if session_id in self.agents:
            await self.agents[session_id].cleanup()
            del self.agents[session_id]

        if session_id in self._locks:
            del self._locks[session_id]

        logger.info(f"Session {session_id} disconnected")

    async def send(self, session_id: str, data: dict):
        """Send message to client"""
        if session_id in self.connections:
            try:
                await self.connections[session_id].send_json(data)
            except Exception as e:
                logger.error(f"Failed to send to {session_id}: {e}")

    async def handle_message(self, session_id: str, data: dict):
        """Handle incoming message from client"""

        agent = self.agents.get(session_id)
        if not agent:
            await self.send(session_id, {
                "type": "error",
                "message": "Agent not initialized"
            })
            return

        message = data.get("message", "").strip()
        if not message:
            return

        # Prevent concurrent messages (agent maintains state)
        lock = self._get_lock(session_id)

        async with lock:
            try:
                # Stream responses from agent
                async for event in agent.chat(message):
                    await self.send(session_id, event)

            except asyncio.TimeoutError:
                await self.send(session_id, {
                    "type": "error",
                    "message": "Request timed out"
                })
            except Exception as e:
                logger.exception(f"Error in chat: {e}")
                await self.send(session_id, {
                    "type": "error",
                    "message": str(e)
                })


# Global manager instance
manager = ConnectionManager()
```

---

## Migrace

### Checklist

#### Fáze 1: Příprava ✅
- [x] Backup současného kódu
- [x] Vytvořit feature branch
- [x] Projít dokumentaci SDK znovu

#### Fáze 2: Nativní tools ✅
- [x] Upravit allowed_tools na nativní
- [x] Nastavit cwd na sandbox path
- [x] Zmenšit MCP server na E2B-only
- [x] Upravit system prompt (preset + append)
- [ ] Otestovat basic flow (bude v Fázi 7)

#### Fáze 3: Subagenti ✅
- [x] Definovat code-reviewer agent
- [x] Definovat error-fixer agent
- [x] Přidat agents do options
- [ ] Otestovat Task tool (bude v Fázi 7)

#### Fáze 4: Hooks ✅
- [x] Implementovat PostToolUse hook
- [x] Implementovat PreToolUse logging
- [x] Přidat hooks do options
- [ ] Otestovat self-correction (bude v Fázi 7)

#### Fáze 5: ClaudeSDKClient ✅
- [x] Změnit na ClaudeSDKClient (již implementováno v agent.py)
- [x] Implementovat conversation memory (ClaudeSDKClient automaticky)
- [x] Upravit WebSocket handler (ConnectionManager drží agents per session)
- [ ] Otestovat multi-turn conversation (bude v Fázi 7)

#### Fáze 6: Permissions ✅
- [x] Implementovat permission callback
- [x] Přidat can_use_tool do options
- [ ] Otestovat blocked commands (bude v Fázi 7)

#### Fáze 7: Testing (Partial) 🔄
- [x] Backend imports and starts correctly
- [x] Permission callback tests pass
- [x] Agent configuration validates
- [ ] End-to-end test: vytvoření app (manual testing required)
- [ ] Test: build failure → self-correction (manual testing required)
- [ ] Test: multi-turn conversation (manual testing required)
- [ ] Test: subagent delegation (manual testing required)
- [ ] Performance test (manual testing required)

---

## Zdroje

- [Claude Agent SDK Docs](/docs/SDK/)
- [SDK Python Reference](/docs/SDK/python.md)
- [Subagents Guide](/docs/SDK/guide-subagents.md)
- [Custom Tools Guide](/docs/SDK/guide-custom-tools.md)
- [Permissions Guide](/docs/SDK/guide-permissions.md)
- [Claude Code CLI](https://code.claude.com/docs/en/cli-reference)

---

*Dokument vytvořen: 2024-11-28*
*Autor: Claude Code analysis*
