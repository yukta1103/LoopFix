# 🤖 AutoDebug Agent

An autonomous coding agent that **writes code, executes it, reads errors, and fixes itself** — iterating until the solution passes or it hits the limit.

Built with **LangGraph** + **DeepSeek-Coder (local via Ollama)** + **Streamlit**.

---

## Demo

> Give it a problem → watch it write, fail, reason about the error, and fix — live.

![Agent loop: write → execute → debug → repeat](assets/demo.gif)

---

## How It Works

```
Problem
   ↓
Write Code  ──→  Execute  ──→  ✅ Pass → Done
                    ↓
                 ❌ Fail
                    ↓
              Read Error + Traceback
                    ↓
              Rewrite Code
                    ↓
               Execute again...
```

The agent runs as a **LangGraph state machine** with three nodes:
- `write_code` — generates an initial solution
- `execute_code` — runs it in a subprocess sandbox, captures stdout/stderr
- `debug_code` — rewrites based on the error message

The full reasoning trace (every attempt, every error, every fix) is displayed in the UI.

---

## Stack

| Component | Tool |
|---|---|
| Agent framework | LangGraph |
| LLM | DeepSeek-Coder 6.7B via Ollama (fully local) |
| Code execution | Python subprocess sandbox |
| UI | Streamlit |

---

## Setup

**1. Install Ollama** → [ollama.com](https://ollama.com)

**2. Pull the model:**
```bash
ollama pull deepseek-coder:6.7b
```

**3. Install dependencies:**
```bash
pip install -r requirements.txt
```

**4. Run:**
```bash
streamlit run ui/app.py
```

---

## Project Structure

```
autodebug-agent/
├── agent/
│   └── graph.py        # LangGraph agent (state, nodes, routing)
├── ui/
│   └── app.py          # Streamlit interface
├── problems/           # Sample benchmark problems
├── requirements.txt
└── README.md
```

---

## Results

Benchmarked on 20 LeetCode Easy problems:

| Metric | Score |
|---|---|
| Pass on first attempt | ~60% |
| Pass within 3 iterations | ~80% |
| Pass within 5 iterations | ~85% |

*(Run your own benchmark — results will vary by problem type)*

---

## Why This Project?

Most LLM demos stop at "generate code." This project is about **closing the loop** — the agent doesn't just write, it reasons about failure and recovers. That's the core of agentic systems being built at companies like Cursor, Cognition, and Replit.