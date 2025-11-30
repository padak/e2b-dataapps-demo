import { NextResponse } from "next/server"
import { queryData, listSchemas, listTables } from "@/keboola"

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const selectedSchema = searchParams.get("schema")
  const selectedTable = searchParams.get("table")

  // Check if Keboola is configured
  const hasConfig =
    process.env.KBC_URL &&
    process.env.KBC_TOKEN &&
    process.env.WORKSPACE_ID &&
    process.env.BRANCH_ID

  if (!hasConfig) {
    return NextResponse.json({
      configured: false,
      error: "Keboola not configured",
      envStatus: {
        KBC_URL: !!process.env.KBC_URL,
        KBC_TOKEN: !!process.env.KBC_TOKEN,
        WORKSPACE_ID: !!process.env.WORKSPACE_ID,
        BRANCH_ID: !!process.env.BRANCH_ID,
      },
    })
  }

  try {
    // Step 1: Get schemas
    console.log("[api/keboola] Fetching schemas...")
    const allSchemas = await listSchemas()

    // Filter to useful schemas only
    const schemas = allSchemas.filter(
      (s) => s.startsWith("in.c-") || s.startsWith("out.c-") || s.startsWith("WORKSPACE_")
    )
    console.log("[api/keboola] Schemas:", schemas)

    // If no schema selected, load ALL schemas with their tables (for instant picker)
    if (!selectedSchema) {
      console.log("[api/keboola] Loading all tables for all schemas...")
      const schemaTablesMap: Record<string, string[]> = {}

      // Fetch tables for all schemas in parallel
      const tablePromises = schemas.map(async (schema) => {
        try {
          const tables = await listTables(schema)
          return { schema, tables }
        } catch (err) {
          console.error(`[api/keboola] Error loading tables for ${schema}:`, err)
          return { schema, tables: [] }
        }
      })

      const results = await Promise.all(tablePromises)
      results.forEach(({ schema, tables }) => {
        schemaTablesMap[schema] = tables
      })

      console.log("[api/keboola] Loaded all schema tables:", Object.keys(schemaTablesMap).length, "schemas")

      return NextResponse.json({
        configured: true,
        schemas,
        schemaTablesMap,
        tables: [],
        data: [],
      })
    }

    // Step 2: Get tables for selected schema (fallback, shouldn't be needed)
    console.log(`[api/keboola] Fetching tables from ${selectedSchema}...`)
    const tables = await listTables(selectedSchema)
    console.log("[api/keboola] Tables:", tables)

    // If no table selected, return tables list
    if (!selectedTable) {
      return NextResponse.json({
        configured: true,
        schemas,
        schema: selectedSchema,
        tables,
        data: [],
      })
    }

    // Step 3: Query the selected table
    const limit = parseInt(searchParams.get("limit") || "100", 10)
    console.log(`[api/keboola] Querying ${selectedSchema}.${selectedTable} (limit: ${limit})...`)

    // Run data query and count query in parallel
    const [data, countResult] = await Promise.all([
      queryData<Record<string, unknown>>(
        `SELECT * FROM "${selectedSchema}"."${selectedTable}" LIMIT ${limit}`
      ),
      queryData<{ count: number }>(
        `SELECT COUNT(*) as count FROM "${selectedSchema}"."${selectedTable}"`
      ),
    ])

    const totalRows = countResult[0]?.count || data.length
    console.log(`[api/keboola] Got ${data.length} rows (total: ${totalRows})`)

    return NextResponse.json({
      configured: true,
      schemas,
      schema: selectedSchema,
      tables,
      tableName: selectedTable,
      data,
      rowCount: data.length,
      totalRows,
    })
  } catch (error) {
    console.error("[api/keboola] Error:", error)
    return NextResponse.json({
      configured: true,
      error: error instanceof Error ? error.message : String(error),
    })
  }
}
