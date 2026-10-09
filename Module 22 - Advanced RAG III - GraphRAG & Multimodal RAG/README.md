# Module 22 — Advanced RAG III: GraphRAG & Multimodal RAG

> **Not built yet.** This is the build plan. Paste `../AGENT_RULES.md` + this file to Claude Code when you're ready.

## Goal in one line

Two RAG techniques for things vector search **cannot** do — multi-hop relationship questions (GraphRAG) and answers that live in charts (Multimodal) — each demonstrated against a baseline that **fails**.

## Why this module exists

Vector search finds text that *sounds similar* to your question. That breaks in two specific ways:

1. **Relationships.** "Which actors worked with directors who also directed a film after 2015?" — no single chunk contains that answer. It requires *hops* across facts. That's a graph query.
2. **Non-text.** If the answer is only in a bar chart, embedding the surrounding paragraphs won't find it.

**The baseline comparison is the whole module.** Building GraphRAG proves nothing unless you also show plain vector search doing worse on the same question.

## Setup

```bash
cd "Module 22 - Advanced RAG III - GraphRAG & Multimodal RAG"
uv init --no-readme --name module22-graphrag-multimodal --python 3.12
rm main.py
uv add langgraph==1.2.0 langchain==1.3.1 langchain-groq python-dotenv pydantic \
       langchain-neo4j neo4j langchain-experimental \
       pymupdf pillow langchain-huggingface sentence-transformers faiss-cpu
cp "../Module 8 - RAG & Human-in-the-Loop/.env" .env
printf 'NEO4J_URI=\nNEO4J_USERNAME=neo4j\nNEO4J_PASSWORD=\n' >> .env
```

Neo4j **Aura free tier** at neo4j.com/aura — real instance required, not mocked.

## Files to create

```
graphrag.py          Neo4j + LLMGraphTransformer + GraphCypherQAChain
multimodal_rag.py    PyMuPDF extraction + vision summaries
baseline_vector.py   plain vector RAG, for the required comparison
RESULTS.md           both comparisons, with the generated Cypher pasted in
NOTES.md             your own notes afterwards
```

## Requirements — GraphRAG (`graphrag.py`)

- **Real Neo4j Aura free instance.** Not a mock.
- **`LLMGraphTransformer` with explicit `allowed_nodes` / `allowed_relationships`.** This is **mandatory, not optional** — unconstrained extraction produces garbage graphs.
- **`GraphCypherQAChain` with `verbose=True`** so the generated Cypher is visible. **Include that Cypher in your results** — don't suppress it.
- Test data with a **genuine multi-hop question** — something plain vector search provably cannot answer. Show the vector version failing or doing worse.

## Requirements — Multimodal RAG (`multimodal_rag.py`)

- A **real PDF with at least one chart/table that matters** to the answer. Not a text-only PDF.
- **`fitz` (PyMuPDF)** extraction of text + tables (as markdown) + images, each tagged with `modality` in metadata.
- **Vision-model summaries of images** used for *retrieval*; the **original image** sent to the vision model again at *answer time* for the specific question.
- A question whose answer is **only** in a chart — proving the multimodal path is load-bearing, not decorative.

## Acceptance criteria

- [ ] **GraphRAG:** the multi-hop question gets a correct answer, **and you show the generated Cypher**.
- [ ] **Multimodal:** the chart-only question gets a correct answer, **and a text-only RAG baseline is shown failing or doing worse** on the same question.

## Pitfalls specific to this module

- **Groq may not have a vision model available to you.** Check the live model list (`AGENT_RULES.md` #1) before planning around one. If there's no vision model on your Groq key, you need a Google (Gemini) or OpenAI key for the multimodal half. **Check this before you start** — it's the module's main blocker.
- **Neo4j Aura free instances pause after a few days idle** and take a minute to resume. "Connection refused" is usually a sleeping instance, not your code.
- **Aura requires the `neo4j+s://` scheme** (encrypted). Using `bolt://` fails with a confusing TLS error.
- **`allowed_nodes`/`allowed_relationships` are genuinely load-bearing.** Skip them and you get 40 node types, half of them synonyms, and Cypher that matches nothing. Start with 3–4 node types and 2–3 relationship types.
- **Generated Cypher is often wrong on the first try.** That's why `verbose=True` is required — you need to see the query to know whether a wrong answer came from bad Cypher or a bad graph.
- **Make the multi-hop question genuinely multi-hop.** If one sentence in your source contains the whole answer, vector search will get it right and your comparison proves nothing. Construct test data where the two facts live in separate places.
- **`langchain-experimental`** hosts `LLMGraphTransformer` — expect API churn; check the installed version's signature rather than trusting older examples.
- PDFs with charts: a chart rendered as **vector graphics** may not extract as an image at all. Verify `fitz` actually found images (`len(page.get_images())`) before building on it. A scanned/screenshotted chart is safer test data.

## Further steps & ideas

- Combine: a graph where image summaries are nodes, so you can hop from a chart to related entities.
- Compare three retrievers on one question set — vector, graph, hybrid — and score with Module 16's harness.
- Visualise the extracted graph in Neo4j Browser and screenshot it. Great portfolio material, and it makes extraction mistakes obvious instantly.
- Use your own lecture slides as the multimodal source — slides are mostly charts and diagrams, which is exactly the case that needs this.
- Write the "when would I actually reach for this?" paragraph honestly. Both techniques are heavier than plain RAG; knowing when *not* to use them is the senior judgment.
