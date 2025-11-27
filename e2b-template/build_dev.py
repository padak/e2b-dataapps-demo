#!/usr/bin/env python3
"""Build the Streamlit template for development/testing."""

from pathlib import Path
from dotenv import load_dotenv

# Load .env from parent directory
load_dotenv(Path(__file__).parent.parent / ".env")

from e2b import Template, default_build_logger
from template import template


if __name__ == "__main__":
    print("🔨 Building E2B Streamlit template (dev)...")
    print("   This will take a few minutes on first build.")
    print()

    Template.build(
        template,
        alias="keboola-streamlit-dev",
        on_build_logs=default_build_logger(),
    )

    print()
    print("✅ Template built! Use with:")
    print('   Sandbox.create(template="keboola-streamlit-dev")')
