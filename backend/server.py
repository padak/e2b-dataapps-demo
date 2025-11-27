#!/usr/bin/env python3
"""
E2B Streamlit Launcher - Backend API
FastAPI server with SSE streaming for real-time logs.
"""

import asyncio
import json
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from e2b_code_interpreter import Sandbox

# Load environment
load_dotenv()

# Store active sandboxes
active_sandboxes: dict[str, Sandbox] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Cleanup sandboxes on shutdown."""
    yield
    for sandbox_id, sandbox in active_sandboxes.items():
        try:
            sandbox.kill()
        except Exception:
            pass
    active_sandboxes.clear()


app = FastAPI(
    title="E2B Streamlit Launcher API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LaunchRequest(BaseModel):
    code: str
    envVars: dict[str, str] | None = None
    packages: list[str] | None = None


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


def extract_dependencies(code: str) -> list[str]:
    """Extract likely pip dependencies from imports in the code."""
    deps = set()

    for line in code.split("\n"):
        line = line.strip()
        if line.startswith("import ") or line.startswith("from "):
            if line.startswith("from "):
                module = line.split()[1].split(".")[0]
            else:
                module = line.split()[1].split(".")[0]

            if module in IMPORT_TO_PIP:
                deps.add(IMPORT_TO_PIP[module])

    return sorted(deps)


def get_sandbox_env_vars() -> dict[str, str]:
    """Get environment variables to pass to sandbox from .env file."""
    FORWARD_KEYS = [
        "WORKSPACE_ID",
        "BRANCH_ID",
        "KBC_URL",
        "KBC_TOKEN",
    ]

    result = {}
    for key in FORWARD_KEYS:
        value = os.environ.get(key)
        if value:
            result[key] = value.strip()

    return result


async def stream_launch(
    code: str,
    template: str | None = None,
    port: int = 8501,
    extra_env_vars: dict[str, str] | None = None,
    extra_packages: list[str] | None = None,
) -> AsyncGenerator[str, None]:
    """
    Stream the sandbox launch process as SSE events.
    """
    start_time = time.time()
    sandbox = None

    def elapsed() -> str:
        return f"{time.time() - start_time:.2f}s"

    def send_event(event_type: str, **data) -> str:
        return f"data: {json.dumps({'type': event_type, **data})}\n\n"

    try:
        # Step 1: Detect dependencies + merge with extra packages
        yield send_event("log", message=f"Detecting dependencies...", status="info")
        deps = set(extract_dependencies(code))
        if extra_packages:
            deps.update(extra_packages)
        deps = sorted(deps)

        if deps:
            yield send_event("log", message=f"Found: {', '.join(deps)}", status="success")
        else:
            yield send_event("log", message="No external dependencies detected", status="info")

        # Step 2: Create sandbox
        yield send_event("status", status="creating")
        use_template = bool(template)

        if use_template:
            yield send_event("log", message=f"Creating sandbox from template '{template}'...", status="info")
        else:
            yield send_event("log", message="Creating sandbox...", status="info")

        env_vars = get_sandbox_env_vars()
        # Merge extra env vars from frontend
        if extra_env_vars:
            env_vars.update(extra_env_vars)
            yield send_event("log", message=f"Added {len(extra_env_vars)} custom env vars", status="info")

        # Run sandbox creation in thread pool (it's blocking)
        loop = asyncio.get_event_loop()

        def create_sandbox():
            if use_template:
                return Sandbox.create(template=template, timeout=300, envs=env_vars)
            return Sandbox.create(timeout=300, envs=env_vars)

        sandbox = await loop.run_in_executor(None, create_sandbox)

        yield send_event("log", message=f"Sandbox ready! ID: {sandbox.sandbox_id} ({elapsed()})", status="success")
        active_sandboxes[sandbox.sandbox_id] = sandbox

        # Step 3: Install dependencies (if no template)
        if not use_template:
            yield send_event("status", status="installing")
            yield send_event("log", message="Installing uv package manager...", status="info")

            await loop.run_in_executor(
                None,
                lambda: sandbox.commands.run("curl -LsSf https://astral.sh/uv/install.sh | sh")
            )
            await loop.run_in_executor(
                None,
                lambda: sandbox.commands.run("export PATH=$HOME/.local/bin:$PATH")
            )

            if deps:
                deps_str = " ".join(deps)
                yield send_event("log", message=f"Installing: {deps_str}", status="info")
                await loop.run_in_executor(
                    None,
                    lambda: sandbox.commands.run(f"~/.local/bin/uv pip install --system {deps_str}")
                )
                yield send_event("log", message="Dependencies installed", status="success")
        else:
            yield send_event("log", message="Skipping dependency installation (pre-installed in template)", status="success")

        # Step 4: Upload script
        yield send_event("status", status="uploading")
        yield send_event("log", message="Uploading script...", status="info")

        remote_path = "/home/user/app.py"
        await loop.run_in_executor(
            None,
            lambda: sandbox.files.write(remote_path, code)
        )
        yield send_event("log", message=f"Uploaded to {remote_path}", status="success")

        # Step 5: Get public URL
        host = sandbox.get_host(port)
        public_url = f"https://{host}"
        yield send_event("log", message=f"Public URL: {public_url}", status="success")

        # Step 6: Start Streamlit
        yield send_event("status", status="starting")
        yield send_event("log", message="Starting Streamlit server...", status="info")

        if use_template:
            streamlit_cmd = (
                f"/home/user/.venv/bin/streamlit run {remote_path} "
                f"--server.port {port} "
                f"--server.headless true "
                f"--server.address 0.0.0.0 "
                f"--browser.gatherUsageStats false"
            )
        else:
            streamlit_cmd = (
                f"~/.local/bin/uv run streamlit run {remote_path} "
                f"--server.port {port} "
                f"--server.headless true "
                f"--server.address 0.0.0.0 "
                f"--browser.gatherUsageStats false"
            )

        # Start in background
        await loop.run_in_executor(
            None,
            lambda: sandbox.commands.run(streamlit_cmd, background=True)
        )

        # Wait for Streamlit to start
        await asyncio.sleep(3)

        yield send_event("log", message=f"Streamlit running! Total time: {elapsed()}", status="success")
        yield send_event("ready", url=public_url, sandboxId=sandbox.sandbox_id)

    except Exception as e:
        error_msg = str(e)
        yield send_event("error", message=error_msg)

        # Cleanup on error
        if sandbox:
            try:
                sandbox.kill()
                active_sandboxes.pop(sandbox.sandbox_id, None)
            except Exception:
                pass


@app.post("/api/launch")
async def launch_sandbox(
    request: LaunchRequest,
    template: str = Query(default=""),
    port: int = Query(default=8501),
):
    """
    Launch a Streamlit app in E2B sandbox.
    Returns SSE stream of progress updates.
    """
    if not os.environ.get("E2B_API_KEY"):
        raise HTTPException(status_code=500, detail="E2B_API_KEY not configured")

    return StreamingResponse(
        stream_launch(
            code=request.code,
            template=template if template else None,
            port=port,
            extra_env_vars=request.envVars,
            extra_packages=request.packages,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.delete("/api/sandbox/{sandbox_id}")
async def stop_sandbox(sandbox_id: str):
    """Stop and cleanup a running sandbox."""
    sandbox = active_sandboxes.pop(sandbox_id, None)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, sandbox.kill)
        return {"status": "stopped", "sandbox_id": sandbox_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sandboxes")
async def list_sandboxes():
    """List all active sandboxes."""
    return {
        "sandboxes": [
            {"id": sid, "status": "running"}
            for sid in active_sandboxes.keys()
        ]
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "e2b_configured": bool(os.environ.get("E2B_API_KEY")),
    }


# Scripts directory management
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"


@app.get("/api/scripts")
async def list_scripts():
    """List all Python scripts in the scripts directory."""
    if not SCRIPTS_DIR.exists():
        return {"scripts": []}

    scripts = []
    for file in SCRIPTS_DIR.glob("*.py"):
        scripts.append({
            "name": file.name,
            "path": str(file.relative_to(SCRIPTS_DIR.parent)),
        })

    return {"scripts": sorted(scripts, key=lambda x: x["name"])}


@app.get("/api/scripts/{script_name}")
async def get_script(script_name: str):
    """Get the content of a specific script."""
    script_path = SCRIPTS_DIR / script_name

    if not script_path.exists():
        raise HTTPException(status_code=404, detail="Script not found")

    if not script_path.suffix == ".py":
        raise HTTPException(status_code=400, detail="Only Python scripts are allowed")

    # Security check - ensure path is within scripts directory
    try:
        script_path.resolve().relative_to(SCRIPTS_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    content = script_path.read_text()
    return {"name": script_name, "content": content}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
