#!/usr/bin/env python3
"""
E2B Streamlit Runner - MVP Demo
Demonstrates how fast E2B sandbox can spin up a Streamlit app.

Usage:
    python run_streamlit.py <path_to_script.py> [--port PORT]

Loads environment variables from .env file automatically.
"""

import argparse
import os
import sys
import time
import webbrowser
from pathlib import Path

from dotenv import load_dotenv
from e2b_code_interpreter import Sandbox

# Load .env file from current directory or script directory
load_dotenv()


VERBOSE = False


def timestamp(start_time: float) -> str:
    """Return elapsed time since start."""
    elapsed = time.time() - start_time
    return f"[{elapsed:6.2f}s]"


def log(start_time: float, message: str, level: str = "INFO"):
    """Print timestamped log message."""
    ts = timestamp(start_time)
    prefix = {"INFO": "→", "OK": "✓", "ERR": "✗", "STREAM": "│", "DEBUG": "  ·"}
    symbol = prefix.get(level, "→")
    print(f"{ts} {symbol} {message}")


def debug(start_time: float, message: str):
    """Print debug message only in verbose mode."""
    if VERBOSE:
        log(start_time, message, "DEBUG")


def get_sandbox_env_vars() -> dict[str, str]:
    """Get environment variables to pass to sandbox from .env file."""
    # Keys to forward to sandbox (loaded from .env)
    FORWARD_KEYS = [
        "WORKSPACE_ID",
        "BRANCH_ID",
        "KBC_URL",
        "KBC_TOKEN",
        # Add more keys here as needed
    ]

    result = {}
    for key in FORWARD_KEYS:
        value = os.environ.get(key)
        if value:
            result[key] = value.strip()

    return result


def extract_dependencies(script_path: Path) -> list[str]:
    """Extract likely pip dependencies from imports in the script."""
    # Common mapping of import names to pip packages
    IMPORT_TO_PIP = {
        "streamlit": "streamlit",
        "pandas": "pandas",
        "plotly": "plotly",
        "httpx": "httpx",
        "numpy": "numpy",
        "matplotlib": "matplotlib",
        "seaborn": "seaborn",
        "sklearn": "scikit-learn",
        "scipy": "scipy",
        "requests": "requests",
        "altair": "altair",
        "bokeh": "bokeh",
        "pydantic": "pydantic",
    }

    deps = set()
    content = script_path.read_text()

    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("import ") or line.startswith("from "):
            # Extract module name
            if line.startswith("from "):
                module = line.split()[1].split(".")[0]
            else:
                module = line.split()[1].split(".")[0]

            if module in IMPORT_TO_PIP:
                deps.add(IMPORT_TO_PIP[module])

    return sorted(deps)


def run_streamlit_in_e2b(
    script_path: Path,
    port: int = 8501,
    open_browser: bool = True,
    template: str | None = None,
):
    """
    Upload and run a Streamlit script in E2B sandbox.

    Args:
        script_path: Path to the Streamlit Python script
        port: Port for Streamlit (default 8501)
        open_browser: Whether to open browser automatically
        template: E2B template name (e.g. 'streamlit-dev'). If None, uses default and installs deps.
    """
    start_time = time.time()
    use_template = template is not None

    # Load env vars from .env file
    env_vars = get_sandbox_env_vars()

    print("\n" + "=" * 60)
    print("🚀 E2B Streamlit Runner - MVP Demo")
    print("=" * 60)
    log(start_time, f"Script: {script_path}")
    log(start_time, f"Port: {port}")
    if template:
        log(start_time, f"Template: {template} (pre-installed deps)", "OK")
    else:
        log(start_time, "Template: default (will install deps at runtime)")
    if env_vars:
        log(start_time, f"Env vars: {', '.join(env_vars.keys())}")
    if VERBOSE:
        log(start_time, "Verbose mode: ON", "DEBUG")
    print("-" * 60)

    # Step 1: Detect dependencies (for info, or for installation if no template)
    log(start_time, "Detecting dependencies from imports...")
    deps = extract_dependencies(script_path)
    log(start_time, f"Found: {', '.join(deps)}", "OK")

    # Step 2: Create sandbox
    if use_template:
        log(start_time, f"Creating E2B sandbox from template '{template}'...")
        debug(start_time, "Using pre-built template - deps already installed!")
    else:
        log(start_time, "Creating E2B sandbox...")
    debug(start_time, "Calling E2B API to provision sandbox VM...")
    debug(start_time, "This includes: VM allocation, network setup, filesystem init")

    t0 = time.time()
    if use_template:
        sandbox = Sandbox.create(template=template, timeout=300, envs=env_vars)
    else:
        sandbox = Sandbox.create(timeout=300, envs=env_vars)
    sandbox_created = time.time()

    log(start_time, f"Sandbox ready! ID: {sandbox.sandbox_id}", "OK")
    log(start_time, f"Sandbox creation took: {sandbox_created - t0:.2f}s", "OK")

    if VERBOSE:
        debug(start_time, f"Template: {template or 'default'}")
        if not use_template:
            debug(start_time, "Breakdown (estimated):")
            debug(start_time, "  - API request + auth: ~0.1-0.3s")
            debug(start_time, "  - VM allocation: ~0.5-1.0s")
            debug(start_time, "  - Container start: ~0.3-0.5s")
            debug(start_time, "  - Network setup: ~0.2-0.3s")
            debug(start_time, "  - Filesystem ready: ~0.1-0.2s")
            debug(start_time, "  - Network latency: varies by location")

    try:
        # Step 3 & 4: Install uv and dependencies (SKIP if using template)
        if not use_template:
            log(start_time, "Installing uv package manager...")
            debug(start_time, "Downloading uv from astral.sh...")
            t0 = time.time()
            sandbox.commands.run("curl -LsSf https://astral.sh/uv/install.sh | sh")
            sandbox.commands.run("export PATH=$HOME/.local/bin:$PATH")
            debug(start_time, f"uv install took: {time.time() - t0:.2f}s")
            log(start_time, "uv installed", "OK")

            if deps:
                deps_str = " ".join(deps)
                log(start_time, f"Installing dependencies: {deps_str}")
                debug(start_time, "Using 'uv pip install --system' for fast installation")
                debug(start_time, "uv resolves deps in parallel, downloads from cache when possible")

                t0 = time.time()
                result = sandbox.commands.run(
                    f"~/.local/bin/uv pip install --system {deps_str}",
                    on_stdout=lambda data: log(start_time, data.strip(), "STREAM") if data.strip() else None,
                    on_stderr=lambda data: log(start_time, f"[pip] {data.strip()}", "STREAM") if data.strip() else None,
                )
                debug(start_time, f"Dependencies install took: {time.time() - t0:.2f}s")
                log(start_time, "Dependencies installed", "OK")
        else:
            log(start_time, "Skipping dependency installation (pre-installed in template)", "OK")

        # Step 5: Upload the script
        log(start_time, "Uploading script to sandbox...")
        debug(start_time, f"Reading local file: {script_path}")
        script_content = script_path.read_text()
        debug(start_time, f"Script size: {len(script_content)} bytes, {len(script_content.splitlines())} lines")
        remote_path = f"/home/user/{script_path.name}"
        t0 = time.time()
        sandbox.files.write(remote_path, script_content)
        debug(start_time, f"Upload took: {time.time() - t0:.2f}s")
        log(start_time, f"Uploaded to {remote_path}", "OK")

        # Step 6: Get public URL
        debug(start_time, f"Requesting public URL for port {port}...")
        host = sandbox.get_host(port)
        public_url = f"https://{host}"
        debug(start_time, f"E2B provides HTTPS proxy to sandbox port {port}")
        log(start_time, f"Public URL: {public_url}", "OK")

        # Step 7: Start Streamlit in background
        log(start_time, "Starting Streamlit server...")
        debug(start_time, "Running streamlit with: headless=true, address=0.0.0.0")

        if use_template:
            # Template has streamlit in venv - use full path
            streamlit_cmd = (
                f"/home/user/.venv/bin/streamlit run {remote_path} "
                f"--server.port {port} "
                f"--server.headless true "
                f"--server.address 0.0.0.0 "
                f"--browser.gatherUsageStats false"
            )
        else:
            # Need to use uv run for default sandbox
            streamlit_cmd = (
                f"~/.local/bin/uv run streamlit run {remote_path} "
                f"--server.port {port} "
                f"--server.headless true "
                f"--server.address 0.0.0.0 "
                f"--browser.gatherUsageStats false"
            )

        # Start in background with streaming
        process = sandbox.commands.run(
            streamlit_cmd,
            background=True,
            on_stdout=lambda data: log(start_time, data.strip(), "STREAM") if data.strip() else None,
            on_stderr=lambda data: log(start_time, f"[stderr] {data.strip()}", "ERR") if data.strip() else None,
        )

        # Wait a bit for Streamlit to start
        log(start_time, "Waiting for Streamlit to start...")
        time.sleep(3)

        # Summary
        total_time = time.time() - start_time
        print("\n" + "=" * 60)
        print("✅ STREAMLIT RUNNING!")
        print("=" * 60)
        print(f"  🌐 URL: {public_url}")
        print(f"  ⏱️  Total startup time: {total_time:.2f}s")
        print(f"  📦 Sandbox ID: {sandbox.sandbox_id}")

        if VERBOSE:
            print("-" * 60)
            print("  📊 Time breakdown:")
            print(f"     Sandbox creation: {sandbox_created - start_time:.2f}s")
            if not use_template:
                print(f"     → With custom template this could be ~3-5s total!")
                print("-" * 60)
                print("  💡 To speed up:")
                print("     1. Build custom template: cd e2b-template && make build-dev")
                print("     2. Run with: python run_streamlit.py script.py --template streamlit-dev")
            else:
                print(f"     ✨ Using template saved ~8s of dependency installation!")

        print("=" * 60)
        print("\n📡 Streaming logs (Ctrl+C to stop)...\n")

        # Open browser
        if open_browser:
            webbrowser.open(public_url)

        # Keep running and streaming logs
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        log(start_time, "Shutting down...", "INFO")
        sandbox.kill()
        log(start_time, "Sandbox terminated", "OK")
        print("=" * 60)

    except Exception as e:
        log(start_time, f"Error: {e}", "ERR")
        sandbox.kill()
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Run a Streamlit app in E2B sandbox",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Without template (slower, ~12s, no build needed)
  python run_streamlit.py scripts/example1.py

  # With custom template (faster, ~4s, requires build first)
  python run_streamlit.py scripts/example1.py --template keboola-streamlit-dev

  # Build template first:
  cd e2b-template && make build-dev

Environment variables are loaded from .env file automatically.
Required in .env:
  E2B_API_KEY     - Your E2B API key
  KBC_TOKEN       - Keboola token (for data apps)
  KBC_URL         - Keboola URL
  BRANCH_ID       - Keboola branch ID
  WORKSPACE_ID    - Keboola workspace ID
        """
    )
    parser.add_argument("script", type=Path, help="Path to Streamlit Python script")
    parser.add_argument("--port", type=int, default=8501, help="Streamlit port (default: 8501)")
    parser.add_argument("-t", "--template", type=str, default=None,
                        help="E2B template name (e.g. 'streamlit-dev'). Skips runtime dependency installation.")
    parser.add_argument("--no-browser", action="store_true",
                        help="Don't open browser automatically")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show detailed debug information")

    args = parser.parse_args()

    # Validate script exists
    if not args.script.exists():
        print(f"Error: Script not found: {args.script}")
        sys.exit(1)

    # Check E2B_API_KEY is set
    if not os.environ.get("E2B_API_KEY"):
        print("Error: E2B_API_KEY not found in .env file")
        sys.exit(1)

    # Set verbose mode
    global VERBOSE
    VERBOSE = args.verbose

    # Run!
    run_streamlit_in_e2b(
        script_path=args.script,
        port=args.port,
        open_browser=not args.no_browser,
        template=args.template,
    )


if __name__ == "__main__":
    main()
