# TraceBack — Hackathon Judging & Presentation Guide 🏆

## ⏱️ The 90-Second Pitch

> "Every developer knows the pain: your application crashes in production, throwing a cryptic stack trace. You spend 30 minutes reading logs, tracking down who wrote that line, writing a quick patch, and hoping you didn't break something else.
> 
> **TraceBack turns that 30-minute headache into a 3-second verified resolution.**
> 
> When your Python project crashes, TraceBack intercepts the real traceback, reads the surrounding function context, runs Git blame to identify how and when the bug was introduced, asks a local open-source LLM (`qwen2.5-coder:3b`) for a minimal unified diff, and automatically generates a regression test.
> 
> Most importantly: **AI proposes. Developer approves. TraceBack verifies.**
> We never touch your code without your approval. Once approved, TraceBack executes pytest against the patch and the application. If it passes, you get a verified fix. If it fails, it rolls back automatically with zero data loss.
> 
> All running 100% locally with zero cloud dependencies or API keys."

---

## 🎯 Live 3-Minute Demonstration Script

| Time | Step | Action | Talking Point |
|------|------|--------|---------------|
| **0:00 - 0:30** | The Problem | Show `demo_project/auth.py` | "Here is a real authentication service. Notice line 3: `trust_level` defaults to 0, which triggers an unhandled `ZeroDivisionError` when a standard user logs in." |
| **0:30 - 1:00** | The Crash & Parse | Click **"Run Demo Crash"** | "TraceBack runs the code in an isolated subprocess, captures the real stderr, parses the stack frames, and inspects Git history via `git blame` to see who wrote this line." |
| **1:00 - 1:45** | The AI Diagnosis | Review Diagnosis & Diff | "Local Qwen2.5-Coder analyzes the code context and generates: 1) a natural root-cause explanation in 3 modes (Beginner, Developer, Expert), 2) an interactive Monaco visual diff, and 3) an automated pytest regression test." |
| **1:45 - 2:30** | The Approval & Verification | Click **"Approve & Verify Fix"** | "Watch our autonomous verification pipeline: Patch is applied -> Regression test runs -> Existing test suite runs -> Application restarts -> 100% tests pass -> Fix Verified." |
| **2:30 - 3:00** | Safety & Telemetry | Show Git & Analytics | "If tests had failed, TraceBack would have automatically reverted the changes. All data is recorded in the Investigation & Patch Registry." |

---

## 💡 Key Judge Talking Points

### 1. "Is this just a ChatGPT wrapper?"
**No.** TraceBack is a complete developer platform built from scratch:
- Real CPython traceback parser with regex state extraction across 25+ exception types.
- Deep Git CLI integration extracting commit SHAs, author timestamps, and line-level blames.
- Local inference using Ollama and Qwen2.5-Coder:3b — **no OpenAI API keys, no telemetry, no cloud costs**.
- Interactive Monaco Diff Editor (same engine as VS Code).
- Deterministic multi-stage Pytest verification engine with automatic rollback.

### 2. "How do you guarantee code safety?"
TraceBack adheres to strict safety boundaries:
1. **Human-in-the-loop**: AI code is never automatically saved without developer confirmation.
2. **Pre-patch snapshotting**: Every patch creates an isolated file backup reference before touch.
3. **Exit-code gating**: No success badge is ever displayed unless `pytest` process actually exits with code `0`.
4. **Auto-rollback**: Any test failure triggers instantaneous restoration of original file states.

### 3. "What tech stack did you choose and why?"
- **Backend**: FastAPI + Python 3.14 for native AST parsing, subprocess handling, and asynchronous API throughput.
- **AI Engine**: Ollama with `qwen2.5-coder:3b` for fast, private, low-latency code repair.
- **Frontend**: React 19 + Vite + Tailwind CSS + Monaco Editor + Lucide Icons for a fluid, dark-mode developer experience reminiscent of Cursor and Linear.

---

## 🗺️ Product Roadmap

- [ ] **Multi-Language Support**: Expand beyond Python to TypeScript, Go, and Rust stack traces.
- [ ] **IDE Extensions**: VS Code and JetBrains plugins for in-editor one-click crash resolution.
- [ ] **CI/CD Integration**: GitHub Action that catches workflow failures and opens PRs with verified fixes and regression tests attached.
- [ ] **Multi-File Context Graph**: AST-based dependency graph traversal for complex multi-module bugs.
