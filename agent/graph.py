import subprocess
import tempfile
import os
import re
import json
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_community.llms import Ollama

builder_llm = Ollama(model="deepseek-coder:6.7b", temperature=0.2)
breaker_llm = Ollama(model="deepseek-coder:6.7b", temperature=0.8)  # higher temp = more creative attacks

MAX_ROUNDS = 4

# ─── State ────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    problem: str
    code: str
    test_cases: list[dict]       # [{input, expected, explanation}]
    test_results: list[dict]     # [{input, expected, actual, passed, explanation}]
    all_passed: bool
    rounds: int
    trace: list[dict]            # full debate history

# ─── Node: Builder ────────────────────────────────────────────────────────────

def builder_write(state: AgentState) -> AgentState:
    """Builder writes/rewrites the solution."""
    is_first = state["rounds"] == 0

    if is_first:
        prompt = f"""You are an expert Python programmer. Return ONLY valid Python code.
No explanations. No markdown. No prose. Define a function that solves the problem.
The function must be named 'solve' and return the answer (do not print).

Problem:
{state['problem']}
"""
    else:
        failed = [t for t in state["test_results"] if not t["passed"]]
        failed_summary = "\n".join(
            f"- Input: {t['input']} | Expected: {t['expected']} | Got: {t['actual']}\n  Why it's tricky: {t['explanation']}"
            for t in failed
        )
        prompt = f"""You are an expert Python programmer. Return ONLY valid Python code.
No explanations. No markdown. No prose. Fix the function named 'solve'.

Problem:
{state['problem']}

Current broken code:
{state['code']}

Failed test cases (with explanations of WHY they're tricky):
{failed_summary}
"""

    code = _strip_markdown(builder_llm.invoke(prompt).strip())
    state["code"] = code
    state["rounds"] = state["rounds"] + 1

    state["trace"].append({
        "round": state["rounds"],
        "agent": "builder",
        "code": code,
        "note": "Initial solution." if is_first else f"Rewrote after {len(failed)} failed test(s)."
    })
    return state


# ─── Node: Breaker ────────────────────────────────────────────────────────────

def breaker_attack(state: AgentState) -> AgentState:
    """Breaker generates adversarial test cases with explanations."""
    prompt = f"""You are an adversarial tester trying to break Python code.
Generate 5 tricky test cases for the function 'solve' below.
Focus on edge cases: empty inputs, negatives, duplicates, large numbers, off-by-one errors, type issues.

Problem:
{state['problem']}

Code to attack:
{state['code']}

Return ONLY a JSON array, no markdown, no explanation outside JSON:
[
  {{
    "input": <the exact argument(s) to pass to solve(), as a JSON value>,
    "expected": <the correct expected output as a JSON value>,
    "explanation": <one sentence: why this test case could break the code>
  }},
  ...
]
"""
    raw = breaker_llm.invoke(prompt).strip()
    test_cases = _parse_json(raw)

    state["test_cases"] = test_cases
    state["trace"].append({
        "round": state["rounds"],
        "agent": "breaker",
        "test_cases": test_cases,
        "note": f"Generated {len(test_cases)} adversarial test cases."
    })
    return state


# ─── Node: Execute Tests ──────────────────────────────────────────────────────

def execute_tests(state: AgentState) -> AgentState:
    """Run the solution against all breaker test cases."""
    results = []

    for tc in state["test_cases"]:
        inp = tc.get("input")
        expected = tc.get("expected")
        explanation = tc.get("explanation", "")

        # Build a test script
        test_code = f"""
import json
{state['code']}

try:
    inp = json.loads({json.dumps(json.dumps(inp))})
    if isinstance(inp, list) and len(inp) > 0 and isinstance(inp[0], list):
        result = solve(*inp)
    elif isinstance(inp, list):
        result = solve(inp)
    else:
        result = solve(inp)
    print(json.dumps(result))
except Exception as e:
    print(f"ERROR: {{e}}")
"""
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as f:
            f.write(test_code)
            tmp_path = f.name

        try:
            result = subprocess.run(
                ["python", tmp_path],
                capture_output=True, text=True, timeout=10
            )
            actual_raw = result.stdout.strip()
            if actual_raw.startswith("ERROR:"):
                actual = actual_raw
                passed = False
            else:
                try:
                    actual = json.loads(actual_raw)
                    passed = actual == expected
                except:
                    actual = actual_raw
                    passed = str(actual).strip() == str(expected).strip()
        except subprocess.TimeoutExpired:
            actual = "TimeoutError"
            passed = False
        finally:
            os.unlink(tmp_path)

        results.append({
            "input": inp,
            "expected": expected,
            "actual": actual,
            "passed": passed,
            "explanation": explanation
        })

    state["test_results"] = results
    state["all_passed"] = all(r["passed"] for r in results)

    state["trace"].append({
        "round": state["rounds"],
        "agent": "executor",
        "results": results,
        "all_passed": state["all_passed"],
        "note": f"{sum(r['passed'] for r in results)}/{len(results)} tests passed."
    })
    return state


# ─── Routing ──────────────────────────────────────────────────────────────────

def should_continue(state: AgentState) -> str:
    if state["all_passed"]:
        return "end"
    if state["rounds"] >= MAX_ROUNDS:
        return "end"
    return "attack"  # breaker attacks again with new test cases


# ─── Graph ────────────────────────────────────────────────────────────────────

def build_graph():
    g = StateGraph(AgentState)
    g.add_node("builder", builder_write)
    g.add_node("breaker", breaker_attack)
    g.add_node("executor", execute_tests)

    g.set_entry_point("builder")
    g.add_edge("builder", "breaker")
    g.add_edge("breaker", "executor")
    g.add_conditional_edges("executor", should_continue, {
        "end": END,
        "attack": "builder"   # builder sees failures, rewrites, breaker attacks again
    })

    return g.compile()


def run_agent(problem: str) -> AgentState:
    graph = build_graph()
    initial_state: AgentState = {
        "problem": problem,
        "code": "",
        "test_cases": [],
        "test_results": [],
        "all_passed": False,
        "rounds": 0,
        "trace": []
    }
    return graph.invoke(initial_state)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _strip_markdown(text: str) -> str:
    match = re.search(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    lines = text.strip().splitlines()
    code_lines = []
    code_started = False
    code_starters = ("def ", "class ", "import ", "from ", "print(", "if ", "for ", "while ", "return ", "#", "    ")
    for line in lines:
        if not code_started:
            if line.strip().startswith(code_starters) or re.match(r"^[a-zA-Z_]\w*\s*=", line):
                code_started = True
        if code_started:
            code_lines.append(line)
    return "\n".join(code_lines).strip() if code_lines else text.strip()


def _parse_json(text: str) -> list:
    text = re.sub(r"```(?:json)?\n?", "", text).replace("```", "").strip()
    try:
        return json.loads(text)
    except:
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
    return []