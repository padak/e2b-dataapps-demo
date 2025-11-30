# DataTable Component

A polished data table component with sorting, filtering, and pagination built on TanStack Table.

## When to Use

Use DataTable when:
- User wants to "show data", "display records", "list items"
- User needs to explore/browse tabular data
- User asks for "data preview" or "sample data"
- User wants to see query results

## Features

- **Auto-column generation** - Just pass data, columns are created automatically
- **Global search** - Filter across all columns
- **Sorting** - Click column headers to sort
- **Pagination** - Navigate through large datasets
- **Loading state** - Built-in loading indicator
- **Responsive** - Works on all screen sizes

## Basic Usage

```tsx
import { DataTable } from "@/components/curated/data-table/DataTable"

// Minimal - just pass data
<DataTable data={users} />

// With title and description
<DataTable
  data={orders}
  title="Recent Orders"
  description="Last 100 orders from the database"
/>
```

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `data` | `T[]` | required | Array of data objects |
| `columns` | `ColumnDef<T>[]` | auto | Custom column definitions |
| `searchable` | `boolean` | `true` | Enable global search |
| `searchPlaceholder` | `string` | `"Search..."` | Search input placeholder |
| `pageSize` | `number` | `10` | Rows per page |
| `paginated` | `boolean` | `true` | Enable pagination |
| `sortable` | `boolean` | `true` | Enable column sorting |
| `title` | `string` | - | Table title |
| `description` | `string` | - | Table description |
| `loading` | `boolean` | `false` | Show loading state |
| `emptyMessage` | `string` | `"No data available"` | Empty state message |

## Examples

### Simple Data Display

```tsx
const users = [
  { id: 1, name: "John", email: "john@example.com" },
  { id: 2, name: "Jane", email: "jane@example.com" },
]

<DataTable data={users} title="Users" />
```

### With Custom Columns

```tsx
import { ColumnDef } from "@tanstack/react-table"

const columns: ColumnDef<Order>[] = [
  { accessorKey: "id", header: "Order ID" },
  { accessorKey: "customer", header: "Customer" },
  {
    accessorKey: "total",
    header: "Total",
    cell: ({ getValue }) => `$${getValue<number>().toFixed(2)}`
  },
]

<DataTable data={orders} columns={columns} />
```

### Loading State

```tsx
<DataTable
  data={[]}
  loading={isLoading}
  title="Loading data..."
/>
```

### Large Dataset with Pagination

```tsx
<DataTable
  data={allRecords}
  pageSize={25}
  paginated
  title="All Records"
  description={`${allRecords.length} total records`}
/>
```

## Integration with Keboola Data

```tsx
// In a Server Component or API route
const data = await queryData("SELECT * FROM customers LIMIT 100")

// In the page
<DataTable
  data={data}
  title="Customers"
  description="Sample of customer data from Keboola"
  searchable
  paginated
/>
```

## Styling

The component uses Tailwind CSS and follows the shadcn/ui design system:
- Integrates with dark/light mode
- Uses `muted`, `border`, `background` color tokens
- Hover states on rows
- Responsive on mobile

## Notes for Agent

1. **Default to auto-columns** - Don't define columns unless user needs custom formatting
2. **Always enable search** - Users expect to filter data
3. **Use appropriate pageSize** - 10 for dashboards, 25+ for full-page tables
4. **Add title/description** - Helps user understand the data context
5. **Handle loading states** - Show loading while fetching data
