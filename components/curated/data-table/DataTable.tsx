"use client"

import { useState } from "react"
import {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  VisibilityState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table"
import { ArrowUpDown, ChevronLeft, ChevronRight, ChevronDown, Search } from "lucide-react"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

interface DataTableProps<TData> {
  /** Array of data to display */
  data: TData[]
  /** Column definitions - if not provided, columns are auto-generated from data keys */
  columns?: ColumnDef<TData>[]
  /** Enable global search */
  searchable?: boolean
  /** Placeholder for search input */
  searchPlaceholder?: string
  /** Number of rows per page (default: 10) */
  pageSize?: number
  /** Enable pagination */
  paginated?: boolean
  /** Enable sorting */
  sortable?: boolean
  /** Enable column visibility toggle */
  columnToggle?: boolean
  /** Table title */
  title?: string
  /** Table description */
  description?: string
  /** Loading state */
  loading?: boolean
  /** Empty state message */
  emptyMessage?: string
  /** Additional class name */
  className?: string
}

/**
 * DataTable - A curated data table component built with shadcn/ui and TanStack Table.
 */
export function DataTable<TData extends Record<string, unknown>>({
  data,
  columns: customColumns,
  searchable = true,
  searchPlaceholder = "Filter...",
  pageSize = 10,
  paginated = true,
  sortable = true,
  columnToggle = true,
  title,
  description,
  loading = false,
  emptyMessage = "No results.",
  className,
}: DataTableProps<TData>) {
  const [sorting, setSorting] = useState<SortingState>([])
  const [globalFilter, setGlobalFilter] = useState("")
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({})

  // Auto-generate columns from data keys if not provided
  const columns: ColumnDef<TData>[] = customColumns ?? (
    data.length > 0
      ? Object.keys(data[0]).map((key) => ({
          accessorKey: key,
          header: ({ column }) => {
            if (!sortable) {
              return <span className="font-medium">{formatHeader(key)}</span>
            }
            return (
              <Button
                variant="ghost"
                size="sm"
                className="-ml-3 h-8 data-[state=open]:bg-accent"
                onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
              >
                <span>{formatHeader(key)}</span>
                <ArrowUpDown className="ml-2 h-3.5 w-3.5" />
              </Button>
            )
          },
          cell: ({ getValue }) => {
            const value = getValue()
            return <CellValue value={value} />
          },
        }))
      : []
  )

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: paginated ? getPaginationRowModel() : undefined,
    getSortedRowModel: sortable ? getSortedRowModel() : undefined,
    getFilteredRowModel: searchable ? getFilteredRowModel() : undefined,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    onColumnVisibilityChange: setColumnVisibility,
    globalFilterFn: "includesString",
    state: {
      sorting,
      columnFilters,
      globalFilter,
      columnVisibility,
    },
    initialState: {
      pagination: {
        pageSize,
      },
    },
  })

  return (
    <div className={cn("w-full", className)}>
      {/* Header with title and controls */}
      <div className="flex items-center justify-between pb-4">
        <div>
          {title && <h3 className="font-semibold">{title}</h3>}
          {description && (
            <p className="text-sm text-muted-foreground">{description}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {searchable && (
            <div className="relative">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder={searchPlaceholder}
                value={globalFilter ?? ""}
                onChange={(e) => setGlobalFilter(e.target.value)}
                className="h-9 w-[200px] pl-8"
              />
            </div>
          )}
          {columnToggle && columns.length > 0 && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="h-9">
                  Columns
                  <ChevronDown className="ml-2 h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-[180px]">
                {table
                  .getAllColumns()
                  .filter((column) => column.getCanHide())
                  .map((column) => (
                    <DropdownMenuCheckboxItem
                      key={column.id}
                      checked={column.getIsVisible()}
                      onCheckedChange={(value) => column.toggleVisibility(!!value)}
                    >
                      {formatHeader(column.id)}
                    </DropdownMenuCheckboxItem>
                  ))}
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id} className="whitespace-nowrap">
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  {columns.map((_, j) => (
                    <TableCell key={j}>
                      <Skeleton className="h-5 w-full" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && "selected"}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-24 text-center"
                >
                  {emptyMessage}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {paginated && data.length > 0 && (
        <div className="flex items-center justify-between pt-4">
          <p className="text-sm text-muted-foreground">
            {table.getFilteredRowModel().rows.length} row(s) total
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Previous
            </Button>
            <span className="text-sm text-muted-foreground px-2">
              {table.getState().pagination.pageIndex + 1} / {table.getPageCount()}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
            >
              Next
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

// Helper: Format header from key
function formatHeader(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/([A-Z])/g, " $1")
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ")
    .trim()
}

// Helper: Render cell value with proper formatting
function CellValue({ value }: { value: unknown }) {
  if (value === null || value === undefined || value === "") {
    return <span className="text-muted-foreground">—</span>
  }

  if (typeof value === "boolean") {
    return (
      <Badge variant={value ? "default" : "secondary"}>
        {value ? "Yes" : "No"}
      </Badge>
    )
  }

  if (typeof value === "number") {
    return <span className="font-mono text-sm tabular-nums">{value.toLocaleString()}</span>
  }

  if (value instanceof Date) {
    return <span className="text-sm">{value.toLocaleDateString()}</span>
  }

  // JSON objects - render as expandable badge
  if (typeof value === "object") {
    const jsonStr = JSON.stringify(value)
    const isSmall = jsonStr.length < 50

    if (isSmall) {
      return (
        <Badge variant="outline" className="font-mono text-xs font-normal max-w-[200px] truncate">
          {jsonStr}
        </Badge>
      )
    }

    return (
      <details className="group">
        <summary className="cursor-pointer">
          <Badge variant="outline" className="font-mono text-xs font-normal">
            {"{...}"} <span className="text-muted-foreground ml-1">expand</span>
          </Badge>
        </summary>
        <pre className="mt-2 p-2 bg-muted rounded text-xs font-mono overflow-auto max-w-[300px] max-h-[200px]">
          {JSON.stringify(value, null, 2)}
        </pre>
      </details>
    )
  }

  const strValue = String(value)

  // Truncate long strings - make expandable on click
  if (strValue.length > 50) {
    return (
      <details className="group inline">
        <summary className="cursor-pointer list-none">
          <span className="text-sm group-open:hidden">
            {strValue.substring(0, 50)}
            <span className="text-muted-foreground">… ↓</span>
          </span>
          <span className="text-sm hidden group-open:inline text-muted-foreground">
            ↑ collapse
          </span>
        </summary>
        <div className="mt-1 p-2 bg-muted rounded text-sm break-words max-w-[400px]">
          {strValue}
        </div>
      </details>
    )
  }

  return <span className="text-sm">{strValue}</span>
}

export default DataTable
