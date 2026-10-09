import sys
from rag_shared import ingest, search_docs

if __name__ == "__main__":
    pdf = sys.argv[1] if len(sys.argv) > 1 else "sample_notes.pdf"
    n = ingest(pdf)
    print(f"Ingested {n} chunk(s) from {pdf} into faiss_db/\n")

    for q in ["What does a checkpointer do?", "How does dynamic fan-out work?"]:
        print(f"Q: {q}")
        print(search_docs.invoke({"query": q})[:400].replace("\n", " "))
        print()
