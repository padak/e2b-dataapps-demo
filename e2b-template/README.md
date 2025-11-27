# E2B Streamlit Template

Pre-configured E2B sandbox template with Streamlit and common data science packages pre-installed.

## Why?

Default E2B sandbox needs to install packages at runtime (~8-10s).
This template has everything pre-installed, reducing startup to **~0.15-0.5s**.

## Pre-installed Packages

- **streamlit** - Web app framework
- **pandas**, **numpy** - Data manipulation
- **plotly**, **altair**, **matplotlib** - Visualization
- **httpx**, **requests** - HTTP clients
- **python-dotenv**, **pydantic** - Utilities

## Building the Template

```bash
# First time setup
pip install e2b

# Set your API key
export E2B_API_KEY=e2b_xxx

# Build for development
make build-dev

# Build for production
make build-prod
```

## Usage

After building, use with `run_streamlit.py`:

```bash
# With custom template (fast ~3-5s)
python run_streamlit.py scripts/example1.py --template keboola-streamlit-dev

# Without template (slower ~12s, no build needed)
python run_streamlit.py scripts/example1.py
```

Or directly in code:

```python
from e2b_code_interpreter import Sandbox

# Use the pre-built template
sandbox = Sandbox.create(template="keboola-streamlit-dev")

# Streamlit is already installed!
sandbox.commands.run("streamlit run app.py --server.headless true")
```

## Template Structure

- `template.py` - Template definition (packages, setup)
- `build_dev.py` - Build script for dev template
- `build_prod.py` - Build script for prod template
- `Makefile` - Convenience commands
