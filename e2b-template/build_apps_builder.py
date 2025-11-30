#!/usr/bin/env python3
"""Build the Next.js App Builder template."""

from pathlib import Path
from dotenv import load_dotenv

# Load .env from parent directory
load_dotenv(Path(__file__).parent.parent / ".env")

from e2b import Template, default_build_logger
from template_nextjs import template


TEMPLATE_ALIAS = "keboola-apps-builder"


if __name__ == "__main__":
    print("=" * 60)
    print(f"  Building E2B template: {TEMPLATE_ALIAS}")
    print("=" * 60)
    print()
    print("This will take a few minutes on first build.")
    print("The template includes:")
    print("  - Node.js 20")
    print("  - Next.js 14 with TypeScript")
    print("  - Tailwind CSS")
    print("  - shadcn/ui dependencies (Radix UI)")
    print("  - recharts, @tanstack/react-table")
    print("  - lucide-react, framer-motion")
    print()

    Template.build(
        template,
        alias=TEMPLATE_ALIAS,
        on_build_logs=default_build_logger(),
    )

    print()
    print("=" * 60)
    print(f"  Template '{TEMPLATE_ALIAS}' built successfully!")
    print("=" * 60)
    print()
    print("Use with:")
    print(f'   Sandbox.create(template="{TEMPLATE_ALIAS}")')
    print()
