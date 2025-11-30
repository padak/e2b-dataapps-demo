/**
 * Keboola Query Service client for Next.js apps.
 *
 * Environment variables required:
 * - KBC_URL: Keboola connection URL (e.g., https://connection.keboola.com/)
 * - KBC_TOKEN: Storage API token
 * - WORKSPACE_ID: Workspace ID
 * - BRANCH_ID: Branch ID
 */

interface QueryResult {
  columns: { name: string }[]
  data: unknown[][]
  status: string
  message?: string
}

/**
 * Execute a SQL query against Keboola workspace via Query Service.
 */
export async function queryData<T extends Record<string, unknown>>(
  query: string
): Promise<T[]> {
  const kbcUrl = process.env.KBC_URL
  const token = process.env.KBC_TOKEN
  const workspaceId = process.env.WORKSPACE_ID
  const branchId = process.env.BRANCH_ID

  if (!kbcUrl || !token || !workspaceId || !branchId) {
    throw new Error(
      "Missing Keboola environment variables. Required: KBC_URL, KBC_TOKEN, WORKSPACE_ID, BRANCH_ID"
    )
  }

  const queryServiceUrl =
    kbcUrl.replace("connection.", "query.").replace(/\/$/, "") + "/api/v1"

  const headers = {
    "X-StorageAPI-Token": token,
    Accept: "application/json",
    "Content-Type": "application/json",
  }

  // Submit query
  const submitResponse = await fetch(
    `${queryServiceUrl}/branches/${branchId}/workspaces/${workspaceId}/queries`,
    {
      method: "POST",
      headers,
      body: JSON.stringify({ statements: [query] }),
    }
  )

  if (!submitResponse.ok) {
    const error = await submitResponse.text()
    throw new Error(`Query submission failed: ${error}`)
  }

  const submission = await submitResponse.json()
  const jobId = submission.queryJobId

  if (!jobId) {
    throw new Error("Query Service did not return a job identifier")
  }

  // Poll for completion
  const startTime = Date.now()
  const timeout = 60000 // 60 seconds

  while (true) {
    const statusResponse = await fetch(
      `${queryServiceUrl}/queries/${jobId}`,
      { headers }
    )

    if (!statusResponse.ok) {
      throw new Error(`Failed to check query status: ${statusResponse.statusText}`)
    }

    const jobInfo = await statusResponse.json()
    const status = jobInfo.status

    if (status === "completed" || status === "failed" || status === "canceled") {
      if (status !== "completed") {
        throw new Error(`Query ${status}: ${jobInfo.message || "Unknown error"}`)
      }

      // Get results
      const statements = jobInfo.statements || []
      if (!statements.length) {
        return []
      }

      const statementId = statements[0].id
      const resultsResponse = await fetch(
        `${queryServiceUrl}/queries/${jobId}/${statementId}/results`,
        { headers }
      )

      if (!resultsResponse.ok) {
        throw new Error(`Failed to fetch results: ${resultsResponse.statusText}`)
      }

      const results: QueryResult = await resultsResponse.json()
      console.log("[keboola] Results response:", JSON.stringify(results).slice(0, 500))

      // Status might be "completed" or "COMPLETED" or similar
      const resultStatus = results.status?.toLowerCase()
      if (resultStatus !== "completed") {
        throw new Error(
          `Query failed: ${results.message || results.status || JSON.stringify(results).slice(0, 200)}`
        )
      }

      // Transform to array of objects
      const columns = results.columns.map((col) => col.name)
      return results.data.map((row) => {
        const obj: Record<string, unknown> = {}
        columns.forEach((col, i) => {
          obj[col] = row[i]
        })
        return obj as T
      })
    }

    if (Date.now() - startTime > timeout) {
      throw new Error("Query timed out after 60 seconds")
    }

    // Wait before polling again
    await new Promise((resolve) => setTimeout(resolve, 1000))
  }
}

/**
 * Get list of available schemas in the workspace.
 */
export async function listSchemas(): Promise<string[]> {
  const results = await queryData<Record<string, unknown>>("SHOW SCHEMAS")
  return results
    .map((r) => String(r.name ?? r.NAME ?? ""))
    .filter(Boolean)
}

/**
 * Get list of tables in a schema.
 */
export async function listTables(schema: string): Promise<string[]> {
  const results = await queryData<Record<string, unknown>>(
    `SHOW TABLES IN SCHEMA "${schema}"`
  )
  return results
    .map((r) => String(r.name ?? r.NAME ?? r.TABLE_NAME ?? ""))
    .filter(Boolean)
}
