# Curated Components Library

Pre-built, polished UI components for data applications.

## Purpose

When the AI agent generates data apps, it uses these curated components
instead of generating random solutions. This ensures:

- **Consistent look & feel** across all generated apps
- **Tested, production-ready** components
- **Best practices** for data visualization and interaction

## Structure

```
components/curated/
├── data-table/           # Data table with sort, filter, pagination
│   ├── DataTable.tsx     # Component implementation
│   ├── index.ts          # Export
│   └── usage.md          # Documentation for the agent
├── keboola.ts            # Keboola Query Service client
└── index.ts              # All exports
```

## Components

### DataTable
Full-featured data table built on TanStack Table.

**Features:**
- Auto-generated columns from data
- Global search/filter
- Column sorting
- Pagination
- Loading and empty states

**Usage:**
```tsx
import { DataTable } from "@/components/curated"

<DataTable
  data={data}
  title="Users"
  searchable
  paginated
/>
```

## Adding New Components

1. Create folder: `components/curated/{component-name}/`
2. Add component: `{ComponentName}.tsx`
3. Add documentation: `usage.md` (for AI agent)
4. Add export: `index.ts`
5. Register in `components/curated/index.ts`

## Usage Documentation (`usage.md`)

Each component has a `usage.md` file that the AI agent reads to understand:
- When to use the component
- Available props
- Example code
- Best practices

This is injected into the agent's system prompt.
