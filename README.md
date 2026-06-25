# LoopFix

**Two AI agents debate until the code is bulletproof.**

LoopFix is a multi-agent autonomous coding system where a **Builder** agent writes Python solutions and a **Breaker** agent attacks them with adversarial test cases — explaining *why* each one could break the code. They go back and forth until the solution passes every test or hits the round limit.

Built with **LangGraph** + **DeepSeek-Coder 6.7B (local via Ollama)** + **Streamlit**.

---

## How It Works

```
Problem
   ↓
🧠 Builder  →  writes solve() function
   ↓
🔴 Breaker  →  generates 5 adversarial test cases + explains why each could break it
   ↓
⚙️  Executor →  runs solution against every test case
   ↓
All pass? ──→ ✅ Done
Any fail? ──→ 🧠 Builder reads failures + Breaker's explanations → rewrites
   ↓
repeat (up to 4 rounds)...
```

The Breaker doesn't throw random inputs — it *reasons* about vulnerability:
- Empty inputs, negatives, duplicates, large numbers
- Off-by-one errors, type mismatches, unsorted inputs
- Each test case comes with an explanation: *"Testing [-1] because your loop assumes at least 2 elements"*

The full debate — every round, every attack, every fix — is visible in the UI.

---

## Architecture

```
LOOPFIX/
├── agent/
│   └── graph.py      # LangGraph state machine (Builder, Breaker, Executor nodes)
├── ui/
│   └── app.py        # Streamlit debate UI
├── requirements.txt
└── README.md
```

### LangGraph State Machine

| Node | Role |
|---|---|
| `builder` | Writes/rewrites the `solve()` function based on failures |
| `breaker` | Generates 5 adversarial test cases with explanations |
| `executor` | Runs solution against all tests, records pass/fail |

Routing: after execution, if all tests pass → `END`. If any fail and rounds < 4 → back to `builder`.

### Two-Temperature Design
- **Builder** runs at `temperature=0.2` — low, deterministic, focused on correctness
- **Breaker** runs at `temperature=0.8` — higher, more creative adversarial thinking

---

## Benchmark

Evaluated on 8 classic algorithm problems:

| Problem | Category | Result | Rounds to solve |
|---|---|---|---|
| Contains Duplicate | Array / Hashing | ✅ Solved | 1 |
| Fibonacci | Recursion / DP | ✅ Solved | 1 |
| Valid Parentheses | Stack | ✅ Solved | 1 |
| Two Sum | Hashmap | ✅ Solved | 2 |
| 3Sum | Two Pointers | ✅ Solved | 2 |
| Longest Palindromic Substring | String / DP | ✅ Solved | 2 |
| Longest Substring (No Repeat) | Sliding Window | ⚠️ 4/5 tests | 4 |
| Merge Intervals | Sorting | ⚠️ 1/5 tests | 4 |

**6/8 problems fully solved (75%). Average rounds to solve: 1.8.**

Harder problems (Merge Intervals, Sliding Window) expose limits of the 6.7B model — a known tradeoff of running fully locally with no API costs.

---

## Stack

| Component | Tool |
|---|---|
| Agent framework | LangGraph |
| LLM | DeepSeek-Coder 6.7B via Ollama (100% local) |
| Code execution | Python subprocess sandbox |
| UI | Streamlit |
| Cost | $0 — no API keys, no cloud |

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

## Why This Project?

Most LLM coding demos stop at "generate code." LoopFix closes the loop in a fundamentally different way — rather than just retrying on errors, the **Breaker agent actively reasons about weaknesses** before they manifest at runtime. This mirrors real adversarial testing practices (red-teaming, fuzzing) and is architecturally closer to how robust software is actually built.

The multi-agent debate pattern — where one model generates and another critiques — is a core primitive in modern AI systems (Constitutional AI, LLM-as-Judge, AutoGen). LoopFix applies it to code generation in a way that's interactive, explainable, and fully local.

---

## Author

**Yukta Kasina** — MS in Artificial Intelligence, Northeastern University  
[Portfolio](https://yukta-portfolio-zeta.vercel.app) · [GitHub](https://github.com/yukta1103) · [LinkedIn](https://linkedin.com/in/yuktakasina)