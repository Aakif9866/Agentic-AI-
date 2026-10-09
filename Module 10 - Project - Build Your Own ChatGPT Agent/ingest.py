"""One-off: load a PDF into faiss_db/ so the `search_docs` tool has something to find.

    uv run python ingest.py sample_notes.pdf
"""
import sys
from tools import ingest_pdf

if __name__ == "__main__":
    pdf = sys.argv[1] if len(sys.argv) > 1 else "sample_notes.pdf"
    print(f"Ingested {ingest_pdf(pdf)} chunk(s) from {pdf} into faiss_db/")
