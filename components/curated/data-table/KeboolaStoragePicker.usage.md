# KeboolaStoragePicker Component

A dropdown picker for selecting Keboola schemas and tables.

## When to Use

Use KeboolaStoragePicker when:
- User needs to select a schema/bucket from Keboola
- User needs to browse available tables
- Building a data browser or explorer UI
- User wants to "pick data", "select table", "choose dataset"

## Features

- **Two-step selection** - First schema, then table
- **Connection indicator** - Green dot shows Keboola is connected
- **Loading state** - Built-in spinner during data loading
- **Refresh button** - Reload current data
- **Scrollable dropdowns** - Handles many schemas/tables

## Basic Usage

```tsx
import { KeboolaStoragePicker } from "@/components/curated/data-table/KeboolaStoragePicker"

<KeboolaStoragePicker
  schemas={["in.c-data", "out.c-results"]}
  tables={["users", "orders", "products"]}
  selectedSchema="in.c-data"
  selectedTable="users"
  onSchemaChange={(schema) => console.log("Schema:", schema)}
  onTableChange={(table) => console.log("Table:", table)}
/>
```

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `schemas` | `string[]` | required | List of available schemas |
| `tables` | `string[]` | required | List of tables in selected schema |
| `selectedSchema` | `string \| null` | required | Currently selected schema |
| `selectedTable` | `string \| null` | required | Currently selected table |
| `loading` | `boolean` | `false` | Show loading state |
| `onSchemaChange` | `(schema: string) => void` | required | Called when schema changes |
| `onTableChange` | `(table: string) => void` | required | Called when table changes |
| `onRefresh` | `() => void` | - | Called when refresh button clicked |

## Integration Pattern

Typically used with `keboola.ts` utilities:

```tsx
"use client"
import { useState, useEffect } from "react"
import { KeboolaStoragePicker } from "@/components/curated/data-table/KeboolaStoragePicker"

export function DataBrowser() {
  const [schemas, setSchemas] = useState<string[]>([])
  const [tables, setTables] = useState<string[]>([])
  const [selectedSchema, setSelectedSchema] = useState<string | null>(null)
  const [selectedTable, setSelectedTable] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  // Fetch schemas on mount
  useEffect(() => {
    fetch("/api/keboola?action=schemas")
      .then(res => res.json())
      .then(data => setSchemas(data.schemas || []))
  }, [])

  // Fetch tables when schema changes
  useEffect(() => {
    if (!selectedSchema) return
    setLoading(true)
    fetch(`/api/keboola?action=tables&schema=${selectedSchema}`)
      .then(res => res.json())
      .then(data => setTables(data.tables || []))
      .finally(() => setLoading(false))
  }, [selectedSchema])

  return (
    <KeboolaStoragePicker
      schemas={schemas}
      tables={tables}
      selectedSchema={selectedSchema}
      selectedTable={selectedTable}
      loading={loading}
      onSchemaChange={(schema) => {
        setSelectedSchema(schema)
        setSelectedTable(null)
      }}
      onTableChange={setSelectedTable}
    />
  )
}
```

## Preloading All Tables (Recommended)

For instant table switching, preload all tables upfront:

```tsx
// API returns: { schemas: [...], schemaTablesMap: { "in.c-data": ["users", "orders"], ... } }
const [schemaTablesMap, setSchemaTablesMap] = useState<Record<string, string[]>>({})

// On mount: fetch all schemas and tables at once
useEffect(() => {
  fetch("/api/keboola?action=schemas")
    .then(res => res.json())
    .then(data => {
      setSchemas(data.schemas)
      setSchemaTablesMap(data.schemaTablesMap)
    })
}, [])

// Tables are instant - no loading needed
<KeboolaStoragePicker
  schemas={schemas}
  tables={selectedSchema ? schemaTablesMap[selectedSchema] : []}
  ...
/>
```

## Notes for Agent

1. **Always pair with DataTable** - Picker selects, table displays
2. **Preload tables if possible** - Better UX with instant switching
3. **Handle loading states** - Show spinner during data fetch
4. **Clear table on schema change** - Reset selection when schema changes
5. **Use KeboolaDataSection for full experience** - Pre-built combination of picker + table
