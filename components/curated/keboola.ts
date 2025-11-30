/**
 * Keboola Query Service client for Next.js apps.
 * Uses official @keboola/query-service SDK.
 *
 * Environment variables required:
 * - KBC_URL: Keboola connection URL (e.g., https://connection.keboola.com/)
 * - KBC_TOKEN: Storage API token
 * - WORKSPACE_ID: Workspace ID
 * - BRANCH_ID: Branch ID
 */

import { Client, JobError } from "@keboola/query-service"

// Lazy-initialized client singleton
let _client: Client | null = null

function getClient(): Client {
  if (!_client) {
    const kbcUrl = process.env.KBC_URL
    const token = process.env.KBC_TOKEN

    if (!kbcUrl || !token) {
      throw new Error(
        "Missing Keboola environment variables. Required: KBC_URL, KBC_TOKEN"
      )
    }

    // Convert connection URL to query service URL
    const baseUrl = kbcUrl.replace("connection.", "query.").replace(/\/$/, "")

    _client = new Client({
      baseUrl,
      token,
    })
  }
  return _client
}

function getWorkspaceConfig() {
  const workspaceId = process.env.WORKSPACE_ID
  const branchId = process.env.BRANCH_ID

  if (!workspaceId || !branchId) {
    throw new Error(
      "Missing Keboola environment variables. Required: WORKSPACE_ID, BRANCH_ID"
    )
  }

  return { workspaceId, branchId }
}

/**
 * Execute a SQL query against Keboola workspace via Query Service.
 */
export async function queryData<T extends Record<string, unknown>>(
  query: string
): Promise<T[]> {
  const client = getClient()
  const { branchId, workspaceId } = getWorkspaceConfig()

  try {
    const results = await client.executeQuery({
      branchId,
      workspaceId,
      statements: [query],
    })

    if (!results.length) {
      return []
    }

    const result = results[0]

    // Transform to array of objects
    const columns = result.columns.map((col) => col.name)
    return result.data.map((row) => {
      const obj: Record<string, unknown> = {}
      columns.forEach((col, i) => {
        obj[col] = row[i]
      })
      return obj as T
    })
  } catch (error) {
    if (error instanceof JobError) {
      throw new Error(`Query failed: ${error.message}`)
    }
    throw error
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

// Re-export SDK types and errors for convenience
export { Client, JobError } from "@keboola/query-service"
export type { QueryResult, Column, JobStatus } from "@keboola/query-service"
