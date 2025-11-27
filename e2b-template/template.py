"""
E2B Streamlit Template - Pre-configured sandbox with Streamlit and common data science packages.

This template pre-installs everything needed to run Streamlit apps instantly,
reducing startup time from ~12s to ~3-5s.
"""

from e2b import Template

# Common packages for Streamlit data apps
STREAMLIT_PACKAGES = [
    # Core
    "streamlit",
    "pandas",
    "numpy",
    # Visualization
    "plotly",
    "altair",
    "matplotlib",
    # HTTP/API
    "httpx",
    "requests",
    # Utilities
    "python-dotenv",
    "pydantic",
]

template = (
    Template()
    .from_image("e2bdev/base")
    # Install uv (fast Python package manager)
    .run_cmd("curl -LsSf https://astral.sh/uv/install.sh | sh")
    # Install Python 3.12
    .run_cmd("/home/user/.local/bin/uv python install 3.12")
    # Create venv with Python 3.12
    .run_cmd("/home/user/.local/bin/uv venv /home/user/.venv --python 3.12")
    # Install all Streamlit packages
    .run_cmd(
        "/home/user/.local/bin/uv pip install --python /home/user/.venv/bin/python "
        + " ".join(STREAMLIT_PACKAGES)
    )
    # Add venv to PATH so streamlit command works directly
    .set_envs({"PATH": "/home/user/.venv/bin:/home/user/.local/bin:$PATH"})
)
