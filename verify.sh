#!/usr/bin/env bash
# Regenerate proof that the modules run, into proofs/ with real timestamps.
#
#   ./verify.sh             # free checks only (no API calls, no cost)
#   ./verify.sh --paid      # everything, ~90 model calls (see VERIFICATION.md)
#   ./verify.sh --module 4  # just one module (free + paid checks for it)
#
# Each module writes proofs/module-<n>.txt containing the actual command and
# its real output. That is stronger evidence than a screenshot: copy-pasteable,
# diffable, and it records WHICH commit produced it.
#
# The venvs are not committed, so a module needs `uv sync` once before its
# check can run. --sync does that for whatever is about to be checked.
set -uo pipefail
cd "$(dirname "$0")"
mkdir -p proofs

PAID=0; SYNC=0; ONLY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --paid) PAID=1 ;;
    --sync) SYNC=1 ;;
    --module) ONLY="$2"; shift ;;
  esac; shift
done

SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "no-git")
STAMP=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
SEEN=""            # modules written this run; the first write truncates the file
                    # (plain string, not an assoc array: macOS ships bash 3.2)

run() {              # run <module-number> <dir> <label> <command...>
  local num="$1" dir="$2" label="$3"; shift 3
  [ -n "$ONLY" ] && [ "$ONLY" != "$num" ] && return 0
  local out="proofs/module-${num}.txt"
  case " $SEEN " in *" $num "*) ;; *) : > "$out"; SEEN="$SEEN $num" ;; esac
  [ "$SYNC" -eq 1 ] && ( cd "$dir" && uv sync --frozen -q )
  printf '=== Module %s — %s\ncommit: %s\nUTC   : %s\ndir   : %s\ncmd   : %s\n%s\n' \
    "$num" "$label" "$SHA" "$STAMP" "$dir" "$*" "$(printf '%.0s-' {1..70})" >> "$out"
  ( cd "$dir" && "$@" ) >> "$out" 2>&1
  local rc=$?
  printf '\n[exit %s]\n\n' "$rc" >> "$out"
  printf '  module %-3s %-34s %s\n' "$num" "$label" \
    "$([ $rc -eq 0 ] && echo PASS || echo FAIL)"
}

# api <module> <dir> <label> <port> <curl-args...>
# Boots uvicorn, waits for /health, fires one real request, always kills it.
# A retry loop beats a fixed sleep: these apps build a model at import.
api() {
  local num="$1" dir="$2" label="$3" port="$4"; shift 4
  run "$num" "$dir" "$label" bash -c '
    port="$1"; shift
    uv run uvicorn api:app --port "$port" --log-level warning & pid=$!
    trap "kill $pid 2>/dev/null" EXIT
    for i in $(seq 1 30); do curl -sf "http://127.0.0.1:$port/health" && break; sleep 2; done
    echo; echo "--- request:"
    curl -sS --max-time 120 "$@"
    echo
  ' _ "$port" "$@"
}

echo "writing proofs/ (commit $SHA)"
echo
echo "--- free checks (no API calls, no key needed) ---"
run 4  "Module 4 - LangGraph Fundamentals/project"              "state/nodes/edges (no LLM)"   uv run python 01_temperature.py
run 17 "Module 17 - LLM Gateway"                                "gateway logic (26 mocked)"    uv run python test_gateway.py
run 18 "Module 18 - Advanced RAG I - Corrective RAG & Self-RAG" "loop caps (pure logic)"       uv run python test_caps.py

if [ "$PAID" -eq 1 ]; then
  echo
  echo "--- paid checks (these call the model) ---"
  run 3  "Module 3 - Agents with LangChain (Single & Multi-Agent)/Multi-Agent AI System" "multi-agent pipeline" uv run python main.py
  run 5  "Module 5 - LangGraph Workflow Patterns"               "dynamic fan-out"      uv run python 01_dynamic_fanout_send.py
  run 6  "Module 6 - Agentic Chatbot - Memory, Streaming & Threads" "memory + threads" uv run python 02_persistent_chatbot.py
  run 7  "Module 7 - Observability & Tools"                     "tool loop"            uv run python 01_single_tool.py
  run 8  "Module 8 - RAG & Human-in-the-Loop"                   "HITL approve/reject"  uv run python 04_hitl_tool_approval.py
  api 9  "Module 9 - Deployment (Docker, CI-CD, Render)"        "FastAPI /health + streaming /chat" 8101 \
          -X POST http://127.0.0.1:8101/chat -H 'content-type: application/json' \
          -d '{"thread_id":"proof","message":"In one sentence: what is a checkpointer?"}'
  api 10 "Module 10 - Project - Build Your Own ChatGPT Agent"   "capstone API end to end" 8102 \
          -X POST http://127.0.0.1:8102/chat -H 'content-type: application/json' \
          -d '{"thread_id":"proof","message":"What is 9*9? Use the calculator."}'
  run 10 "Module 10 - Project - Build Your Own ChatGPT Agent"   "budget guard trips"   uv run python budget_demo.py
  run 11 "Module 11 - Project - TripMate AI (Multi-Agent Travel Planner)" "supervisor" uv run python main.py
  run 12 "Module 12 - MCP (Model Context Protocol)"             "MCP round-trip"       uv run python client.py
  run 13 "Module 13 - LangGraph Subgraphs + Project - AgentWriter AI" "subgraph alone" uv run python research_subgraph.py
  run 14 "Module 14 - Guardrails + Project - Multi-Agent Supervisor System" "5-case guardrail eval" uv run python test_guards.py
  run 16 "Module 16 - AI Agent Evaluation"                      "eval suite (first 8 cases)" uv run python evals/run_evals.py --quick 8
  run 17 "Module 17 - LLM Gateway"                              "real fallback, 3 calls" uv run python live_check.py
  run 18 "Module 18 - Advanced RAG I - Corrective RAG & Self-RAG" "Self-RAG, real KB"  uv run python self_rag.py
  run 18 "Module 18 - Advanced RAG I - Corrective RAG & Self-RAG" "CRAG, real KB"      uv run python crag.py
  run 19 "Module 19 - Project - Self-Correcting Multi-Agent App (Serverless)" "writer/reviewer loop" uv run python graph.py
else
  echo
  echo "(skipped paid checks — re-run with --paid to include them)"
fi

echo
echo "done. proofs/ now holds the transcripts."
echo "For image screenshots: macOS Cmd+Shift+4, or  script -q /dev/null <cmd>  then screenshot."
