# E2B Streamlit Runner

Run Streamlit apps in isolated E2B cloud sandboxes with a single command. Demonstrates how fast E2B can spin up a full Streamlit environment.

## Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/padak/e2b-dataapps-demo.git
cd e2b-dataapps-demo

python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure

Create a `.env` file with your credentials:

```bash
E2B_API_KEY=e2b_xxx          # Get from https://e2b.dev/dashboard

# Optional: For Keboola data apps
KBC_TOKEN=xxx
KBC_URL=https://connection.keboola.com/
BRANCH_ID=xxx
WORKSPACE_ID=xxx
```

### 3. Run

```bash
# Basic usage
python run_streamlit.py scripts/example1.py

# With custom template (faster, requires build first)
python run_streamlit.py scripts/example1.py -t keboola-streamlit-dev

# Verbose mode
python run_streamlit.py scripts/example1.py -v
```

## Sample Output

```
(.venv) $ python ./run_streamlit.py ./scripts/example1.py -v -t keboola-streamlit-dev

============================================================
🚀 E2B Streamlit Runner - MVP Demo
============================================================
[  0.00s] → Script: scripts/example1.py
[  0.00s] → Port: 8501
[  0.00s] ✓ Template: keboola-streamlit-dev (pre-installed deps)
[  0.00s] → Env vars: WORKSPACE_ID, BRANCH_ID, KBC_URL, KBC_TOKEN
[  0.00s]   · Verbose mode: ON
------------------------------------------------------------
[  0.00s] → Detecting dependencies from imports...
[  0.00s] ✓ Found: httpx, pandas, plotly, streamlit
[  0.00s] → Creating E2B sandbox from template 'keboola-streamlit-dev'...
[  0.00s]   · Using pre-built template - deps already installed!
[  0.00s]   · Calling E2B API to provision sandbox VM...
[  0.00s]   · This includes: VM allocation, network setup, filesystem init
[  1.57s] ✓ Sandbox ready! ID: ixd8strv1rz0yuyzufz4c
[  1.57s] ✓ Sandbox creation took: 1.57s
[  1.57s]   · Template: keboola-streamlit-dev
[  1.57s] ✓ Skipping dependency installation (pre-installed in template)
[  1.57s] → Uploading script to sandbox...
[  1.57s]   · Reading local file: scripts/example1.py
[  1.57s]   · Script size: 9847 bytes, 279 lines
[  2.35s]   · Upload took: 0.78s
[  2.35s] ✓ Uploaded to /home/user/example1.py
[  2.35s]   · Requesting public URL for port 8501...
[  2.35s]   · E2B provides HTTPS proxy to sandbox port 8501
[  2.35s] ✓ Public URL: https://8501-ixd8strv1rz0yuyzufz4c.e2b.app
[  2.35s] → Starting Streamlit server...
[  2.35s]   · Running streamlit with: headless=true, address=0.0.0.0
[  2.53s] → Waiting for Streamlit to start...

============================================================
✅ STREAMLIT RUNNING!
============================================================
  🌐 URL: https://8501-ixd8strv1rz0yuyzufz4c.e2b.app
  ⏱️  Total startup time: 5.53s
  📦 Sandbox ID: ixd8strv1rz0yuyzufz4c
------------------------------------------------------------
  📊 Time breakdown:
     Sandbox creation: 1.57s
     ✨ Using template saved ~8s of dependency installation!
============================================================

📡 Streaming logs (Ctrl+C to stop)...
```

## License

MIT - see [LICENSE](LICENSE)
