"use client"

import { useCallback } from "react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { ChevronDown, Database, Table2, RefreshCw, Loader2 } from "lucide-react"

interface KeboolaStoragePickerProps {
  schemas: string[]
  tables: string[]
  selectedSchema: string | null
  selectedTable: string | null
  loading?: boolean
  onSchemaChange: (schema: string) => void
  onTableChange: (table: string) => void
  onRefresh?: () => void
}

/**
 * KeboolaStoragePicker - A picker component for selecting Keboola schemas and tables.
 *
 * @example
 * <KeboolaStoragePicker
 *   schemas={["in.c-data", "out.c-results"]}
 *   tables={["users", "orders"]}
 *   selectedSchema="in.c-data"
 *   selectedTable="users"
 *   onSchemaChange={(schema) => console.log(schema)}
 *   onTableChange={(table) => console.log(table)}
 * />
 */
export function KeboolaStoragePicker({
  schemas,
  tables,
  selectedSchema,
  selectedTable,
  loading = false,
  onSchemaChange,
  onTableChange,
  onRefresh,
}: KeboolaStoragePickerProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* Connection indicator */}
      <span className="inline-flex items-center gap-1.5 text-sm text-muted-foreground mr-2">
        <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
        Keboola
      </span>

      {/* Schema picker */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            className="h-8 gap-1.5 font-normal"
            disabled={loading}
          >
            <Database className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="max-w-[150px] truncate">
              {selectedSchema || "Schema"}
            </span>
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="max-h-[300px] overflow-auto">
          {schemas.length === 0 ? (
            <DropdownMenuItem disabled>No schemas available</DropdownMenuItem>
          ) : (
            schemas.map((schema) => (
              <DropdownMenuItem
                key={schema}
                onClick={() => onSchemaChange(schema)}
                className={selectedSchema === schema ? "bg-accent font-medium" : ""}
              >
                <Database className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
                {schema}
              </DropdownMenuItem>
            ))
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Table picker */}
      {selectedSchema && (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="h-8 gap-1.5 font-normal"
              disabled={loading || tables.length === 0}
            >
              <Table2 className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="max-w-[150px] truncate">
                {selectedTable || "Table"}
              </span>
              <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="max-h-[300px] overflow-auto">
            {tables.length === 0 ? (
              <DropdownMenuItem disabled>No tables found</DropdownMenuItem>
            ) : (
              tables.map((table) => (
                <DropdownMenuItem
                  key={table}
                  onClick={() => onTableChange(table)}
                  className={selectedTable === table ? "bg-accent font-medium" : ""}
                >
                  <Table2 className="h-3.5 w-3.5 mr-2 text-muted-foreground" />
                  {table}
                </DropdownMenuItem>
              ))
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      )}

      {/* Loading indicator */}
      {loading && (
        <span className="inline-flex items-center gap-1.5 text-sm text-muted-foreground">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Loading...
        </span>
      )}

      {/* Refresh button */}
      {selectedTable && onRefresh && !loading && (
        <Button
          variant="ghost"
          size="sm"
          className="h-8 w-8 p-0"
          onClick={onRefresh}
          disabled={loading}
        >
          <RefreshCw className="h-3.5 w-3.5" />
          <span className="sr-only">Refresh</span>
        </Button>
      )}
    </div>
  )
}

export default KeboolaStoragePicker
