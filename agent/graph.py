import subprocess
import tempfile
import os
import re
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_community.llms import Ollama

llm = Ollama(model="deepseek-coder:6.7b", temperature=0.2)

MAX_ITERATIONS = 5

# ─── State ────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    problem: str
    code: str
    execution_output: str
    error: str
    passed: bool
    iterations: int
    trace: list[dict]  # full reasoning history

# ─── Nodes ────────────────────────────────────────────────────────────────────

def write_code(state: AgentState) -> AgentState:
    """Generate code for the problem (first attempt)."""
    prompt = f"""You are a Python coding assistant. Return ONLY valid Python code.
No explanations. No markdown. No prose. Just raw executable Python code.

Problem:
{state['problem']}
"""
    code = llm.invoke(prompt).strip()
    code = _strip_markdown(code)

    state["code"] = code
    state["iterations"] = state.get("iterations", 0) + 1
    state["trace"].append({
        "iteration": state["iterations"],
        "action": "write",
        "code": code,
        "note": "Initial solution generated."
    })
    return state


def execute_code(state: AgentState) -> AgentState:
    """Run the code in a subprocess and capture output or error."""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(state["code"])
        tmp_path = f.name

    try:
        result = subprocess.run(
            ["python", tmp_path],
            capture_output=True, text=True, timeout=10
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if result.returncode == 0:
            state["execution_output"] = stdout
            state["error"] = ""
            state["passed"] = True
        else:
            state["execution_output"] = stdout
            state["error"] = stderr
            state["passed"] = False
    except subprocess.TimeoutExpired:
        state["error"] = "TimeoutError: code took longer than 10 seconds."
        state["passed"] = False
    finally:
        os.unlink(tmp_path)

    state["trace"][-1]["output"] = state["execution_output"]
    state["trace"][-1]["error"] = state["error"]
    state["trace"][-1]["passed"] = state["passed"]
    return state


def debug_code(state: AgentState) -> AgentState:
    """Rewrite code based on the error."""
    prompt = f"""You are a Python debugging assistant. Return ONLY valid Python code.
No explanations. No markdown. No prose. Just raw executable Python code.

Problem:
{state['problem']}

Broken code:
{state['code']}

Error:
{state['error']}
"""
    new_code = llm.invoke(prompt).strip()
    new_code = _strip_markdown(new_code)

    state["code"] = new_code
    state["iterations"] = state.get("iterations", 0) + 1
    state["trace"].append({
        "iteration": state["iterations"],
        "action": "debug",
        "code": new_code,
        "note": f"Fixed after error: {state['error'][:120]}"
    })
    return state


# ─── Routing ──────────────────────────────────────────────────────────────────

def should_continue(state: AgentState) -> str:
    if state["passed"]:
        return "end"
    if state["iterations"] >= MAX_ITERATIONS:
        return "end"
    return "debug"


# ─── Graph ────────────────────────────────────────────────────────────────────

def build_graph():
    g = StateGraph(AgentState)
    g.add_node("write_code", write_code)
    g.add_node("execute_code", execute_code)
    g.add_node("debug_code", debug_code)

    g.set_entry_point("write_code")
    g.add_edge("write_code", "execute_code")
    g.add_conditional_edges("execute_code", should_continue, {
        "end": END,
        "debug": "debug_code"
    })
    g.add_edge("debug_code", "execute_code")

    return g.compile()


def run_agent(problem: str) -> AgentState:
    graph = build_graph()
    initial_state: AgentState = {
        "problem": problem,
        "code": "",
        "execution_output": "",
        "error": "",
        "passed": False,
        "iterations": 0,
        "trace": []
    }
    return graph.invoke(initial_state)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _strip_markdown(text: str) -> str:
    """Extract only the Python code block, stripping prose and markdown fences."""
    # If there's a ```python or ``` block, extract just that
    match = re.search(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Otherwise strip lines until we hit something that looks like code
    lines = text.strip().splitlines()
    code_lines = []
    code_started = False
    code_starters = (
        "def ", "class ", "import ", "from ", "print(",
        "if ", "for ", "while ", "return ", "#", "    "
    )
    for line in lines:
        if not code_started:
            if line.strip().startswith(code_starters) or re.match(r"^[a-zA-Z_]\w*\s*=", line):
                code_started = True
        if code_started:
            code_lines.append(line)

    return "\n".join(code_lines).strip() if code_lines else text.strip()