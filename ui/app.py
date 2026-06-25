import streamlit as st
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agent.graph import run_agent

st.set_page_config(page_title="LoopFix", page_icon="⚔️", layout="wide")

st.title("⚔️ LoopFix")
st.caption("**Builder** writes code. **Breaker** attacks it with adversarial tests + explains why. They debate until the code is bulletproof.")

# ─── Samples ──────────────────────────────────────────────────────────────────

SAMPLES = {
    "3Sum": "Write a function solve(nums) that finds all unique triplets in the list that sum to zero. Return a list of triplets (each sorted). E.g. solve([-1,0,1,2,-1,-4]) → [[-1,-1,2],[-1,0,1]]",
    "Longest Substring": "Write a function solve(s) that returns the length of the longest substring without repeating characters. E.g. solve('abcabcbb') → 3",
    "Valid Parentheses": "Write a function solve(s) that returns True if the string of brackets is valid (every open bracket has a matching close). E.g. solve('()[]{}') → True, solve('(]') → False",
    "Merge Intervals": "Write a function solve(intervals) that merges all overlapping intervals. E.g. solve([[1,3],[2,6],[8,10],[15,18]]) → [[1,6],[8,10],[15,18]]",
}

with st.sidebar:
    st.header("⚙️ Config")
    st.markdown("🧠 **Builder:** deepseek-coder:6.7b")
    st.markdown("🔴 **Breaker:** deepseek-coder:6.7b (temp=0.8)")
    st.markdown("🔁 **Max rounds:** 4")
    st.divider()
    selected = st.selectbox("Load sample problem:", ["Custom"] + list(SAMPLES.keys()))

default = SAMPLES.get(selected, "") if selected != "Custom" else ""
problem = st.text_area("📝 Problem:", value=default, height=120,
    placeholder="Describe a coding problem. The agent will write a solve() function.")

run_btn = st.button("⚔️ Start Debate", type="primary", disabled=not problem.strip())

# ─── Run ──────────────────────────────────────────────────────────────────────

if run_btn and problem.strip():
    st.divider()
    with st.spinner("⚔️ Agents are debating..."):
        result = run_agent(problem.strip())

    # ── Banner
    if result["all_passed"]:
        st.success(f"✅ Builder won — all tests passed after **{result['rounds']} round(s)**!")
    else:
        passed = sum(r["passed"] for r in result["test_results"])
        total = len(result["test_results"])
        st.warning(f"⚠️ Debate ended after {result['rounds']} rounds — {passed}/{total} tests passing.")

    # ── Final state
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("💻 Final Code")
        st.code(result["code"], language="python")
    with col2:
        st.subheader("🧪 Final Test Results")
        for r in result["test_results"]:
            icon = "✅" if r["passed"] else "❌"
            with st.expander(f"{icon} Input: `{r['input']}`"):
                st.markdown(f"**Expected:** `{r['expected']}`")
                st.markdown(f"**Got:** `{r['actual']}`")
                st.markdown(f"**Why tricky:** {r['explanation']}")

    # ── Full debate trace
    st.divider()
    st.subheader("🥊 Full Debate Trace")

    for step in result["trace"]:
        agent = step["agent"]
        round_num = step["round"]

        if agent == "builder":
            with st.expander(f"🧠 Round {round_num} — Builder writes", expanded=(round_num == 1)):
                st.markdown(f"*{step['note']}*")
                st.code(step["code"], language="python")

        elif agent == "breaker":
            with st.expander(f"🔴 Round {round_num} — Breaker attacks"):
                st.markdown(f"*{step['note']}*")
                for i, tc in enumerate(step["test_cases"], 1):
                    st.markdown(f"**Test {i}:** `solve({tc['input']})` → expected `{tc['expected']}`")
                    st.caption(f"💡 {tc['explanation']}")

        elif agent == "executor":
            passed_n = sum(r["passed"] for r in step["results"])
            total_n = len(step["results"])
            icon = "✅" if step["all_passed"] else "❌"
            with st.expander(f"{icon} Round {round_num} — Results: {passed_n}/{total_n} passed"):
                for r in step["results"]:
                    status = "✅" if r["passed"] else "❌"
                    st.markdown(f"{status} `solve({r['input']})` → got `{r['actual']}`, expected `{r['expected']}`")