"use client"

import { useEffect, useState, useCallback } from "react"
import { DataTable, KeboolaStoragePicker } from "@/data-table"
import { Skeleton } from "@/components/ui/skeleton"
import { Database, Table2 } from "lucide-react"

interface KeboolaResponse {
  configured: boolean
  schemas?: string[]
  schemaTablesMap?: Record<string, string[]>
  schema?: string
  tables?: string[]
  tableName?: string
  data?: Record<string, unknown>[]
  rowCount?: number
  totalRows?: number
  error?: string
  envStatus?: Record<string, boolean>
}

// Sample data fallback
const sampleData = [
  { event_id: "evt_001", user_id: "user_123", event_type: "View Product", platform: "web", city: "Prague", country: "CZ" },
  { event_id: "evt_002", user_id: "user_456", event_type: "Add to Cart", platform: "ios", city: "Brno", country: "CZ" },
  { event_id: "evt_003", user_id: "user_123", event_type: "Complete Purchase", platform: "web", city: "Prague", country: "CZ" },
  { event_id: "evt_004", user_id: "user_789", event_type: "View Product", platform: "android", city: "Ostrava", country: "CZ" },
  { event_id: "evt_005", user_id: "user_456", event_type: "Start Checkout", platform: "ios", city: "Brno", country: "CZ" },
]

const FETCH_LIMITS = [100, 500, 1000, 5000] as const

export function KeboolaDataSection() {
  const [loading, setLoading] = useState(true)
  const [loadingData, setLoadingData] = useState(false)
  const [response, setResponse] = useState<KeboolaResponse | null>(null)
  const [schemaTablesMap, setSchemaTablesMap] = useState<Record<string, string[]>>({})
  const [selectedSchema, setSelectedSchema] = useState<string | null>(null)
  const [selectedTable, setSelectedTable] = useState<string | null>(null)
  const [fetchLimit, setFetchLimit] = useState<number>(100)

  // Fetch all schemas and tables on mount
  useEffect(() => {
    fetch("/api/keboola")
      .then((res) => res.json())
      .then((data) => {
        console.log("[KeboolaDataSection] Initial response:", data)
        setResponse(data)
        // Store the schema->tables map for instant filtering
        if (data.schemaTablesMap) {
          setSchemaTablesMap(data.schemaTablesMap)
        }
      })
      .catch((err) => {
        console.error("[KeboolaDataSection] Fetch error:", err)
        setResponse({ configured: false, error: err.message })
      })
      .finally(() => setLoading(false))
  }, [])

  // Handle schema change - instant, no API call needed
  const handleSchemaChange = useCallback((schema: string) => {
    setSelectedSchema(schema)
    setSelectedTable(null)
    // Tables are already loaded in schemaTablesMap, no API call needed!
    console.log(`[KeboolaDataSection] Schema selected: ${schema}, tables:`, schemaTablesMap[schema])
  }, [schemaTablesMap])

  // Fetch data when table changes
  const handleTableChange = useCallback(async (table: string, limit: number = fetchLimit) => {
    if (!selectedSchema) return
    setSelectedTable(table)
    setLoadingData(true)

    try {
      const res = await fetch(
        `/api/keboola?schema=${encodeURIComponent(selectedSchema)}&table=${encodeURIComponent(table)}&limit=${limit}`
      )
      const data = await res.json()
      setResponse(data)
    } catch (err) {
      console.error("[KeboolaDataSection] Error:", err)
    } finally {
      setLoadingData(false)
    }
  }, [selectedSchema, fetchLimit])

  // Handle fetch limit change
  const handleLimitChange = useCallback((newLimit: number) => {
    setFetchLimit(newLimit)
    if (selectedTable) {
      handleTableChange(selectedTable, newLimit)
    }
  }, [selectedTable, handleTableChange])

  // Refresh current selection
  const handleRefresh = useCallback(() => {
    if (selectedSchema && selectedTable) {
      handleTableChange(selectedTable)
    }
  }, [selectedSchema, selectedTable, handleTableChange])

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-[400px] w-full" />
      </div>
    )
  }

  // Not configured - show sample data
  if (!response?.configured) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-2 text-sm text-amber-600 bg-amber-50 rounded-md px-3 py-2 border border-amber-200">
          <span className="h-2 w-2 rounded-full bg-amber-500" />
          Keboola not configured — showing sample data
          {response?.envStatus && (
            <span className="text-xs text-amber-500 ml-auto">
              Missing: {Object.entries(response.envStatus)
                .filter(([, v]) => !v)
                .map(([k]) => k)
                .join(", ")}
            </span>
          )}
        </div>
        <DataTable
          data={sampleData}
          title="Sample Events"
          description="5 sample events"
          searchable
          paginated
          pageSize={10}
          columnToggle
        />
      </div>
    )
  }

  // Error (but configured)
  if (response.error && !response.schemas?.length) {
    return (
      <div className="rounded-md border border-red-200 bg-red-50 p-4">
        <h3 className="font-medium text-red-800">Error loading Keboola</h3>
        <p className="text-sm text-red-600 mt-1">{response.error}</p>
      </div>
    )
  }

  // Connected - show picker and data
  return (
    <div className="space-y-6">
      {/* Picker */}
      <KeboolaStoragePicker
        schemas={response.schemas || []}
        tables={selectedSchema ? (schemaTablesMap[selectedSchema] || []) : []}
        selectedSchema={selectedSchema}
        selectedTable={selectedTable}
        loading={loadingData}
        onSchemaChange={handleSchemaChange}
        onTableChange={handleTableChange}
        onRefresh={handleRefresh}
      />

      {/* Loading state */}
      {loadingData && (
        <div className="space-y-4">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-[400px] w-full" />
        </div>
      )}

      {/* Error message */}
      {response.error && !loadingData && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4">
          <h3 className="font-medium text-red-800">Error</h3>
          <p className="text-sm text-red-600 mt-1">{response.error}</p>
        </div>
      )}

      {/* No selection prompt */}
      {!selectedSchema && !loadingData && (
        <div className="rounded-md border border-dashed p-12 text-center">
          <Database className="h-10 w-10 mx-auto mb-3 text-muted-foreground/50" />
          <p className="text-muted-foreground">Select a schema to browse tables</p>
          <p className="text-sm text-muted-foreground/70 mt-1">
            {response.schemas?.length || 0} schemas, {Object.values(schemaTablesMap).flat().length} tables loaded
          </p>
        </div>
      )}

      {/* Schema selected but no table */}
      {selectedSchema && !selectedTable && !loadingData && !response.error && (
        <div className="rounded-md border border-dashed p-12 text-center">
          <Table2 className="h-10 w-10 mx-auto mb-3 text-muted-foreground/50" />
          <p className="text-muted-foreground">Select a table to view data</p>
          <p className="text-sm text-muted-foreground/70 mt-1">
            {schemaTablesMap[selectedSchema]?.length || 0} tables in {selectedSchema}
          </p>
        </div>
      )}

      {/* Data table */}
      {response.data && response.data.length > 0 && !loadingData && (
        <div className="space-y-4">
          {/* Table info & fetch limit selector */}
          <div className="flex items-center justify-between text-sm">
            <div className="text-muted-foreground">
              Showing <span className="font-medium text-foreground">{response.rowCount?.toLocaleString()}</span> of{" "}
              <span className="font-medium text-foreground">{response.totalRows?.toLocaleString()}</span> total rows
            </div>
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Load:</span>
              {FETCH_LIMITS.map((limit) => (
                <button
                  key={limit}
                  onClick={() => handleLimitChange(limit)}
                  className={`px-2 py-1 text-xs rounded border transition-colors ${
                    fetchLimit === limit
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-background hover:bg-muted border-input"
                  }`}
                >
                  {limit.toLocaleString()}
                </button>
              ))}
            </div>
          </div>
          <DataTable
            data={response.data}
            title={response.tableName}
            description={`${response.schema}.${response.tableName}`}
            searchable
            paginated
            pageSize={10}
            columnToggle
          />
        </div>
      )}

      {/* Empty table */}
      {selectedTable && response.data?.length === 0 && !loadingData && !response.error && (
        <div className="rounded-md border p-8 text-center text-muted-foreground">
          No data in {selectedSchema}.{selectedTable}
        </div>
      )}
    </div>
  )
}
