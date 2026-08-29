# TraceBack 🔍⚡

> **AI-Powered Crash Investigation & Automated Code Repair**  
> *From stack trace to verified fix.*

TraceBack is a developer tool and autonomous debugging engine that analyzes Python crashes, traces them to their exact source and Git commit origin, generates a minimal targeted fix and regression test using local Ollama LLMs (`qwen2.5-coder:3b`), and deterministically verifies the repair before applying it.

---

## 🏛️ Architecture Overview

```
                               ┌────────────────────────────────────────────────────────┐
                               │                    React + Vite UI                     │
                               │  Dashboard │ Monaco Code & Diff │ Command Palette (⌃K) │
                               └───────────────────────────┬────────────────────────────┘
                                                           │ REST APIs
                               ┌───────────────────────────┴────────────────────────────┐
                               │                     FastAPI Engine                     │
                               ├────────────────────────────────────────────────────────┤
                               │  Traceback Parser    Source Analyzer    Git Intelligence│
                               │  Patch Service       Pytest Service     Verification   │
                               └─────────┬──────────────────┬─────────────────┬─────────┘
                                         │                  │                 │
                                  ┌──────┴──────┐    ┌──────┴──────┐    ┌─────┴─────┐
                                  │   Ollama    │    │  Git CLI    │    │  Pytest   │
                                  │(qwen2.5-3b) │    │  (Subproc)  │    │  Engine   │
                                  └─────────────┘    └─────────────┘    └───────────┘
```

---

## 🚀 Key Features

1. **Deterministic Traceback Parsing**: Extracts exception type, message, exact file, line number, containing function, and full stack frames from raw CPython tracebacks across all exception classes.
2. **Source Code Intelligence**: Extracts tight surrounding context windows (30-60 lines), imports, and function signatures without bloating the LLM prompt.
3. **Git Blame & Authorship Attribution**: Runs `git blame -L` to inspect commit hash, author, and commit summary for the broken line to provide context on when the regression was introduced.
4. **Local LLM Diagnosis**: Connects to local Ollama running `qwen2.5-coder:3b` without requiring OpenAI API keys or sending code outside your machine.
5. **Interactive Monaco Diff Editor**: Review proposed code changes side-by-side or inline with visual syntax highlighting and line numbers.
6. **Automatic Pytest Regression Test Generation**: The AI generates a dedicated pytest regression test that reproduces the bug and proves the fix.
7. **Human-In-The-Loop Safety Model**: Patches are never blindly applied. TraceBack creates an isolated backup, applies the unified diff, executes generated regression tests, runs existing project test suites, re-runs the application, and automatically rolls back if verification fails.
8. **Real-time Activity Stream & Telemetry**: Full timeline animation for the 8-step diagnostic pipeline, plus error analytics and crash registry.

---

## 🛠️ Prerequisites

- **Python**: 3.10+ (tested on Python 3.14)
- **Node.js**: v18+ (tested on Node v24)
- **Git**: Installed and available on system `PATH`
- **Ollama**: Installed and running locally (`http://localhost:11434`) with `qwen2.5-coder:3b`

---

## 📦 Installation & Setup

### 1. Set Up Ollama Model
```bash
# Pull the recommended coding model
ollama pull qwen2.5-coder:3b

# Ensure Ollama is running
ollama serve
```

### 2. Backend Setup
```bash
# Clone and enter directory
cd TraceBack

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1   # On Windows
# source venv/bin/activate    # On Linux/macOS

# Install backend dependencies
pip install -r requirements.txt pytest

# Start FastAPI server
uvicorn backend.main:app --reload --port 8000
```
Backend will be live at: `http://localhost:8000` (API Docs at `http://localhost:8000/docs`)

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend dashboard will be live at: `http://localhost:5173`

---

## 🎯 Running the Live Hackathon Demo

1. Open `http://localhost:5173` in your browser.
2. Verify the top right status badge says **`● qwen2.5-coder:3b`** (Ollama connected).
3. Click **"Run Demo Crash"** in the header or dashboard hero.
4. **Watch the live pipeline stream**:
   - `demo_project/auth.py` is executed and crashes with `ZeroDivisionError`.
   - TraceBack captures the real stderr, parses the traceback to `auth.py:3`.
   - Queries `git blame` to find the introducing commit.
   - Prompts local `qwen2.5-coder:3b` to diagnose the root cause.
5. Review the **Monaco Diff Viewer** and **Generated Regression Test**.
6. Click **"Approve & Verify Fix"**.
7. Observe the verification stages:
   - ✓ Patch applied cleanly
   - ✓ Regression test passed
   - ✓ Existing tests passed
   - ✓ Application started with exit code 0
   - **FIX VERIFIED** verdict displayed!

---

## 🔒 Security Model

- **No Remote Code Execution**: TraceBack runs exclusively on your local machine.
- **Path Traversal Protection**: All filesystem reads and writes validate against permitted workspace directories.
- **No Arbitrary Shell Strings**: All subprocess invocations use structured argument arrays rather than raw shell strings.
- **Controlled Patch Application**: Patches are validated for context matching and create automated backup points before applying.

---

## 🧪 Running Backend Unit Tests

```bash
# Run the test suite
python -m pytest tests/ -v
```
All 20 test cases will execute and validate parser correctness and API endpoints.

---

## 📂 Project Structure

```
TraceBack/
├── backend/
│   ├── main.py                  # FastAPI entry point & router mounting
│   ├── config.py                # Centralized settings & path boundaries
│   ├── models/                  # Pydantic schemas (crash, analysis, patch)
│   ├── services/
│   │   ├── traceback_parser.py  # Regex traceback parser for Python exceptions
│   │   ├── source_analyzer.py   # File reader & smart context window builder
│   │   ├── git_service.py       # Safe subprocess Git blame/log/status
│   │   ├── ollama_service.py    # Local Ollama client & prompt engineer
│   │   ├── patch_service.py     # Patch validator, applier & rollback engine
│   │   ├── test_service.py      # Pytest execution engine
│   │   └── verification_service.py # Full multi-stage verification pipeline
│   └── api/                     # REST endpoints (crash, git, patch, analysis, repo)
├── frontend/
│   ├── src/
│   │   ├── components/          # Monaco Code/Diff viewers, timeline, cards
│   │   ├── pages/               # Dashboard, Analyzer, Investigations, Repo
│   │   ├── services/api.js      # REST API client
│   │   └── App.jsx              # Main React container & routing
│   ├── tailwind.config.js       # Dark developer theme tokens
│   └── package.json
├── demo_project/                # Deterministic buggy application for demo
│   ├── auth.py                  # Buggy authentication module (ZeroDivisionError)
│   ├── utils.py                 # Additional buggy utility functions
│   └── tests/test_auth.py       # Existing pytest suite
├── tests/                       # Backend test suite
├── requirements.txt
└── README.md
```
