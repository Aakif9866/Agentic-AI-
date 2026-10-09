# Module 20 — Advanced RAG II: Agentic RAG

> **Not built yet.** This is the build plan. Paste `../AGENT_RULES.md` + this file to Claude Code when you're ready.

## Goal in one line

RAG where an agent **decides** whether to use the knowledge base, answer directly, or search the web — running on a **hosted** vector DB, not local FAISS.

## Why this module exists

Two upgrades over Module 18:

1. **Routing before retrieval.** Not every question needs the knowledge base. "Hi" shouldn't trigger a vector search (you saw this in Module 8), and neither should "what's 2+2".
2. **A hosted vector DB.** FAISS lives in a file on your laptop. Pinecone lives on the internet, which is what you'd actually deploy against — and it forces you to get embedding dimensions right.

## Setup

```bash
cd "Module 20 - Advanced RAG II - Agentic RAG"
uv init --no-readme --name module20-agentic-rag --python 3.12
rm main.py
uv add langgraph==1.2.0 langchain==1.3.1 langchain-groq python-dotenv pydantic \
       langchain-pinecone pinecone langchain-tavily langchain-huggingface \
       sentence-transformers langchain-community langchain-text-splitters pypdf
cp "../Module 8 - RAG & Human-in-the-Loop/.env" .env
cp "../Module 8 - RAG & Human-in-the-Loop/sample_notes.pdf" .
echo "PINECONE_API_KEY=" >> .env    # get a free key at pinecone.io
```

## Files to create

```
ingest_pinecone.py   create the index + upload chunks
main.py              the routing graph
NOTES.md             your own notes afterwards
```

## Requirements

- **Pinecone** (free tier) instead of FAISS — `PineconeVectorStore`, with the index **dimension matched to your embedding model**. `all-MiniLM-L6-v2` = **384**. Confirm before creating the index.
- **An explicit graph**, not a loose ReAct agent:

  ```
  route(kb|direct) → retrieve_kb → grade_kb → generate_from_kb
                                            → search_web → grade_web → generate_from_web
                                                                      → rewrite_query → retrieve_kb (capped)
  ```

- **`RouteDecision`** and **`EvidenceGrade`** as real Pydantic schemas with `Literal` fields. No string matching on LLM output.
- A `source_used` field in state so you can print which path each question took.

## Acceptance criteria

- [ ] Pinecone index **actually created and populated** — show `pc.describe_index(...)` output proving it's real, not mocked.
- [ ] **3 test questions**, printing the actual `source_used` for each:
  1. chitchat/direct → routes away from the KB entirely
  2. in-KB → answered from Pinecone
  3. needs web fallback → goes to Tavily

## Pitfalls specific to this module

- **Dimension mismatch is the #1 Pinecone error.** If you create a 1536-dim index (the OpenAI default everyone copies) and embed with MiniLM (384), every upsert fails. Create the index with `dimension=384`, or print `len(embeddings.embed_query("test"))` first and use that number.
- **Index creation is asynchronous.** Upserting immediately after `create_index` fails because the index isn't ready. Poll `describe_index(...).status['ready']` until it's true.
- **Free-tier Pinecone has one index and limited namespaces.** If you already made one for something else, reuse or delete it.
- **Eventual consistency:** a query right after upsert may return nothing. Wait a few seconds before your first test, or you'll "debug" a non-problem.
- Both schemas need `method="json_mode"` with field names spelled out (`AGENT_RULES.md` #2).
- **The router is the module.** If it sends everything to the KB, you've built Module 8 with extra steps. Test chitchat explicitly and make sure it does *not* retrieve.

## Further steps & ideas

- Add a `namespace` per document source so you can route to *specific* knowledge bases ("search the HR docs" vs "search the eng docs").
- Add metadata filtering: only retrieve chunks from a given page range or document.
- Compare retrieval quality against Module 18's FAISS on the same questions — is hosted actually better, or just more deployable?
- Make `route` a tool call rather than a node, and compare: explicit graph vs agent-decides. The brief prefers the explicit graph; now you'll know why.
- Combine with Module 18's graders for a single best-of-both RAG graph.
