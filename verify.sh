#!/usr/bin/env bash
# Regenerate proof that the modules run, into proofs/ with real timestamps.
#
#   ./verify.sh            # free checks only (no API calls, no cost)
#   ./verify.sh --paid     # everything, ~250 model calls (see VERIFICATION.md)
#   ./verify.sh --module 4 # just one module
#
# Each module writes proofs/<module>.txt containing the actual command and its
# real output. That is stronger evidence than a screenshot: copy-pasteable,
# diffable, and it proves WHICH commit produced it.
set -uo pipefail
cd "$(dirname "$0")"
mkdir -p proofs

PAID=0; ONLY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --paid) PAID=1 ;;
    --module) ONLY="$2"; shift ;;
  esac; shift
done

SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "no-git")
STAMP=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

run() {              # run <module-number> <dir> <label> <command...>
  local num="$1" dir="$2" label="$3"; shift 3
  [ -n "$ONLY" ] && [ "$ONLY" != "$num" ] && return 0
  local out="proofs/module-${num}.txt"
  printf '=== Module %s — %s\ncommit: %s\nUTC   : %s\ncmd   : %s\n%s\n' \
    "$num" "$label" "$SHA" "$STAMP" "$*" "$(printf '%.0s-' {1..70})" >> "$out"
  ( cd "$dir" && "$@" ) >> "$out" 2>&1
  local rc=$?
  printf '\n[exit %s]\n\n' "$rc" >> "$out"
  printf '  module %-3s %-34s %s\n' "$num" "$label" \
    "$([ $rc -eq 0 ] && echo PASS || echo FAIL)"
}

echo "writing proofs/ (commit $SHA)"
echo
echo "--- free checks (no API calls) ---"
run 4  "Module 4 - LangGraph Fundamentals/project"            "state/nodes/edges (no LLM)" uv run python 01_temperature.py
run 18 "Module 18 - Advanced RAG I - Corrective RAG & Self-RAG" "loop caps (pure logic)"   uv run python test_caps.py

if [ "$PAID" -eq 1 ]; then
  echo
  echo "--- paid checks (these call the model) ---"
  run 5  "Module 5 - LangGraph Workflow Patterns"               "dynamic fan-out"      uv run python 01_dynamic_fanout_send.py
  run 6  "Module 6 - Agentic Chatbot - Memory, Streaming & Threads" "memory + threads" uv run python 02_persistent_chatbot.py
  run 7  "Module 7 - Observability & Tools"                     "tool loop"            uv run python 01_single_tool.py
  run 8  "Module 8 - RAG & Human-in-the-Loop"                   "HITL approve/reject"  uv run python 04_hitl_tool_approval.py
  run 11 "Module 11 - Project - TripMate AI (Multi-Agent Travel Planner)" "supervisor" uv run python main.py
  run 12 "Module 12 - MCP (Model Context Protocol)"             "MCP round-trip"       uv run python client.py
  run 13 "Module 13 - LangGraph Subgraphs + Project - AgentWriter AI" "subgraph alone" uv run python research_subgraph.py
  run 14 "Module 14 - Guardrails + Project - Multi-Agent Supervisor System" "5-case guardrail eval" uv run python test_guards.py
  run 16 "Module 16 - AI Agent Evaluation"                      "31-case eval suite"   uv run python evals/run_evals.py
  run 19 "Module 19 - Project - Self-Correcting Multi-Agent App (Serverless)" "writer/reviewer" uv run python graph.py
else
  echo
  echo "(skipped paid checks — re-run with --paid to include them)"
fi

echo
echo "done. proofs/ now holds the transcripts."
echo "For image screenshots: macOS Cmd+Shift+4, or  script -q /dev/null <cmd>  then screenshot."
