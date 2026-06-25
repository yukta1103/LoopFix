import streamlit as st
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent.graph import run_agent

# ─── Page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AutoDebug Agent",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 AutoDebug Agent")
st.caption("Writes code → runs it → reads errors → fixes → repeats. Powered by DeepSeek-Coder + LangGraph.")

# ─── Sample problems ──────────────────────────────────────────────────────────

SAMPLE_PROBLEMS = {
    "FizzBuzz": "Write a program that prints numbers 1 to 30. For multiples of 3 print 'Fizz', for multiples of 5 print 'Buzz', for multiples of both print 'FizzBuzz'.",
    "Fibonacci": "Print the first 15 Fibonacci numbers.",
    "Palindrome Checker": "Write a function is_palindrome(s) that returns True if s is a palindrome. Test it with: 'racecar', 'hello', 'madam'.",
    "Two Sum": "Given a list [2, 7, 11, 15] and target 9, find two numbers that add up to the target and print their indices.",
    "Reverse Words": "Write a function that reverses the words in a sentence. Test with: 'Hello World from Python'. Print the result.",
}

# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Settings")
    st.markdown("**Model:** `deepseek-coder:6.7b` via Ollama")
    st.markdown("**Max iterations:** 5")
    st.markdown("**Execution:** subprocess (local)")
    st.divider()
    st.header("📋 Sample Problems")
    selected_sample = st.selectbox("Load a sample:", ["Custom"] + list(SAMPLE_PROBLEMS.keys()))

# ─── Input ────────────────────────────────────────────────────────────────────

default_problem = SAMPLE_PROBLEMS.get(selected_sample, "") if selected_sample != "Custom" else ""

problem = st.text_area(
    "📝 Describe your coding problem:",
    value=default_problem,
    height=120,
    placeholder="e.g. Write a function that checks if a number is prime and test it on 17, 20, 97."
)

run_btn = st.button("🚀 Run Agent", type="primary", disabled=not problem.strip())

# ─── Run ──────────────────────────────────────────────────────────────────────

if run_btn and problem.strip():
    st.divider()

    with st.spinner("🧠 Agent is thinking..."):
        result = run_agent(problem.strip())

    # ── Summary banner
    if result["passed"]:
        st.success(f"✅ Solved in **{result['iterations']} iteration(s)**!")
    else:
        st.error(f"❌ Could not solve after {result['iterations']} iterations.")

    # ── Final code + output
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("💻 Final Code")
        st.code(result["code"], language="python")
    with col2:
        st.subheader("📤 Output")
        if result["execution_output"]:
            st.code(result["execution_output"])
        if result["error"]:
            st.error(result["error"])

    # ── Reasoning trace
    st.divider()
    st.subheader("🔍 Reasoning Trace")
    st.caption("Every attempt the agent made — what it wrote, what broke, and how it fixed it.")

    for step in result["trace"]:
        iteration = step["iteration"]
        action = step["action"]
        icon = "✏️" if action == "write" else "🔧"
        label = "Initial Write" if action == "write" else f"Debug Attempt"

        with st.expander(f"{icon} Iteration {iteration} — {label}", expanded=(iteration == 1)):
            st.markdown(f"**Note:** {step.get('note', '')}")
            st.code(step.get("code", ""), language="python")

            out = step.get("output", "")
            err = step.get("error", "")
            passed = step.get("passed", False)

            if passed:
                st.success("✅ Passed")
                if out:
                    st.code(out)
            else:
                if out:
                    st.code(out)
                if err:
                    st.error(f"**Error:** {err}")