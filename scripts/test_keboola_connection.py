#!/usr/bin/env python3
"""
Test Keboola Query Service API connection.

This script verifies that the credentials in .env work correctly.
"""

import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


def get_query_service_url(kbc_url: str) -> str:
    """Convert connection URL to query service URL."""
    return kbc_url.replace("connection.", "query.", 1).rstrip("/") + "/api/v1"


def query_data(query: str, branch_id: str, workspace_id: str, token: str, kbc_url: str) -> list[dict]:
    """Execute SQL query via Keboola Query Service."""
    query_service_url = get_query_service_url(kbc_url)
    headers = {
        "X-StorageAPI-Token": token,
        "Accept": "application/json",
    }

    timeout = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=None)

    with httpx.Client(timeout=timeout) as client:
        # Submit query
        print(f"  Submitting query to {query_service_url}...")
        response = client.post(
            f"{query_service_url}/branches/{branch_id}/workspaces/{workspace_id}/queries",
            json={"statements": [query]},
            headers=headers,
        )
        response.raise_for_status()
        job_id = response.json().get("queryJobId")
        print(f"  Job ID: {job_id}")

        # Wait for completion
        print("  Waiting for query to complete...")
        start_ts = time.monotonic()
        while True:
            status_response = client.get(
                f"{query_service_url}/queries/{job_id}",
                headers=headers,
            )
            status_response.raise_for_status()
            job_info = status_response.json()
            status = job_info.get("status")

            if status in {"completed", "failed", "canceled"}:
                break
            if time.monotonic() - start_ts > 60:
                raise TimeoutError("Query timed out after 60 seconds")
            time.sleep(1)

        if status != "completed":
            raise RuntimeError(f"Query failed with status: {status}")

        # Get results
        statements = job_info.get("statements") or []
        if not statements:
            return []

        statement_id = statements[0]["id"]
        results_response = client.get(
            f"{query_service_url}/queries/{job_id}/{statement_id}/results",
            headers=headers,
        )
        results_response.raise_for_status()
        results = results_response.json()

        columns = [col["name"] for col in results.get("columns", [])]
        data_rows = [
            {col_name: value for col_name, value in zip(columns, row)}
            for row in results.get("data", [])
        ]
        return data_rows


def main():
    print("=" * 60)
    print("Keboola Query Service API - Connection Test")
    print("=" * 60)

    # Check environment variables
    kbc_url = os.environ.get("KBC_URL")
    kbc_token = os.environ.get("KBC_TOKEN")
    workspace_id = os.environ.get("WORKSPACE_ID")
    branch_id = os.environ.get("BRANCH_ID")

    print("\n1. Checking environment variables...")
    missing = []
    if not kbc_url:
        missing.append("KBC_URL")
    if not kbc_token:
        missing.append("KBC_TOKEN")
    if not workspace_id:
        missing.append("WORKSPACE_ID")
    if not branch_id:
        missing.append("BRANCH_ID")

    if missing:
        print(f"  ERROR: Missing environment variables: {', '.join(missing)}")
        print(f"  Please check your .env file at: {env_path}")
        sys.exit(1)

    # Clean up values (remove spaces from .env parsing)
    kbc_url = kbc_url.strip()
    kbc_token = kbc_token.strip()
    workspace_id = workspace_id.strip()
    branch_id = branch_id.strip()

    print(f"  KBC_URL: {kbc_url}")
    print(f"  KBC_TOKEN: {kbc_token[:10]}...{kbc_token[-4:]}")
    print(f"  WORKSPACE_ID: {workspace_id}")
    print(f"  BRANCH_ID: {branch_id}")
    print("  ✓ All variables present")

    # Test connection with simple query
    print("\n2. Testing connection with simple query...")
    try:
        result = query_data(
            "SELECT 1 as test_value",
            branch_id, workspace_id, kbc_token, kbc_url
        )
        print(f"  ✓ Connection successful! Result: {result}")
    except Exception as e:
        print(f"  ERROR: Connection failed: {e}")
        sys.exit(1)

    # List available schemas/tables
    print("\n3. Discovering available schemas...")
    try:
        schemas = query_data(
            "SHOW SCHEMAS",
            branch_id, workspace_id, kbc_token, kbc_url
        )
        print(f"  Found {len(schemas)} schemas:")
        for schema in schemas[:10]:  # Show first 10
            name = schema.get("name", schema.get("NAME", "?"))
            print(f"    - {name}")
        if len(schemas) > 10:
            print(f"    ... and {len(schemas) - 10} more")
    except Exception as e:
        print(f"  Warning: Could not list schemas: {e}")

    # Try to find tables
    print("\n4. Looking for tables in workspace...")
    try:
        tables = query_data(
            "SHOW TABLES",
            branch_id, workspace_id, kbc_token, kbc_url
        )
        print(f"  Found {len(tables)} tables in current schema:")
        for table in tables[:10]:
            name = table.get("name", table.get("NAME", table.get("TABLE_NAME", "?")))
            print(f"    - {name}")
        if len(tables) > 10:
            print(f"    ... and {len(tables) - 10} more")
    except Exception as e:
        print(f"  Note: No tables in default schema or error: {e}")

    # Try to query sample data from known table (from example1.py)
    print("\n5. Testing data query (sample from events table)...")
    try:
        sample = query_data(
            '''SELECT * FROM "SAPI_10504"."out.c-amplitude"."events" LIMIT 5''',
            branch_id, workspace_id, kbc_token, kbc_url
        )
        if sample:
            print(f"  ✓ Got {len(sample)} rows")
            print(f"  Columns: {list(sample[0].keys())}")
        else:
            print("  No data returned (table might be empty)")
    except Exception as e:
        print(f"  Note: Could not query events table: {e}")
        print("  (This is OK if the table doesn't exist in your project)")

    print("\n" + "=" * 60)
    print("CONNECTION TEST COMPLETE")
    print("=" * 60)
    print("\n✓ Keboola Query Service API is working!")
    print("  You can use query_data() function to query your data.")


if __name__ == "__main__":
    main()
