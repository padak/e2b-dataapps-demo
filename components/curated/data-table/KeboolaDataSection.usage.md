# KeboolaDataSection Component

A complete, ready-to-use data browser combining KeboolaStoragePicker and DataTable.

## When to Use

Use KeboolaDataSection when:
- User wants "a data browser", "data explorer", "table viewer"
- User says "let me browse Keboola data"
- User needs quick access to see what's in their data
- Building a data exploration app without custom requirements

**Use individual components (DataTable, KeboolaStoragePicker) when:**
- User needs custom layout
- User wants specific features only
- Building more complex UI

## Features

- **All-in-one** - Picker + Table in one component
- **Preloads all schemas/tables** - Instant switching, no loading
- **Configurable row limits** - 100, 500, 1000, 5000 rows
- **Graceful fallback** - Shows sample data if Keboola not configured
- **Error handling** - Shows clear error messages
- **Empty states** - Guides user through selection

## Basic Usage

```tsx
import { KeboolaDataSection } from "@/components/curated/app/KeboolaDataSection"

// Just drop it in - zero configuration needed
export default function Page() {
  return (
    <main className="container py-8">
      <h1 className="text-2xl font-bold mb-6">Data Browser</h1>
      <KeboolaDataSection />
    </main>
  )
}
```

## Props

This component has **no props** - it's fully self-contained.

It reads configuration from:
- `/api/keboola` endpoint (must be implemented)
- Environment variables: `KBC_URL`, `KBC_TOKEN`, `WORKSPACE_ID`, `BRANCH_ID`

## Required API Endpoint

The component expects `/api/keboola` with these actions:

```typescript
// GET /api/keboola (or ?action=schemas)
// Returns all schemas and tables
{
  configured: true,
  schemas: ["in.c-data", "out.c-results"],
  schemaTablesMap: {
    "in.c-data": ["users", "orders"],
    "out.c-results": ["summary"]
  }
}

// GET /api/keboola?schema=in.c-data&table=users&limit=100
// Returns table data
{
  configured: true,
  schema: "in.c-data",
  tableName: "users",
  data: [{ id: 1, name: "John" }, ...],
  rowCount: 100,
  totalRows: 5432
}
```

## States Handled

1. **Loading** - Shows skeleton while fetching
2. **Not configured** - Shows sample data with warning
3. **Error** - Shows error message
4. **No selection** - Prompts to select schema
5. **Schema selected** - Prompts to select table
6. **Data loaded** - Shows DataTable with data

## Customization

If you need to customize, copy this component and modify:

```tsx
// Copy from components/curated/app/KeboolaDataSection.tsx
// Customize as needed
```

## Notes for Agent

1. **Default choice for data browsing** - Use this unless specific requirements
2. **Requires API endpoint** - Must have /api/keboola
3. **Self-contained** - No props, no setup needed
4. **Copy to customize** - It's a boilerplate, modify as needed
