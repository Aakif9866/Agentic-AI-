"""Shared RAG pieces: ingest a PDF into FAISS, and expose search as a tool.

Both 01_rag_tool.py and 02_rag_chatbot.py import from here so the tool is
defined exactly once.
"""
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.tools import tool

# Local, free embeddings — no API key. First run downloads ~90MB.
EMBEDDINGS = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
DB_PATH = "faiss_db"


def ingest(pdf_path: str) -> int:
    """Load a PDF, split it into overlapping chunks, embed them, save the index."""
    docs = PyPDFLoader(pdf_path).load()
    # Real PDFs come out full of padding spaces and hard line breaks. Collapsing that
    # whitespace before chunking noticeably improves retrieval quality.
    for d in docs:
        d.page_content = " ".join(d.page_content.split())
    chunks = RecursiveCharacterTextSplitter(
        chunk_size=400, chunk_overlap=80
    ).split_documents(docs)
    FAISS.from_documents(chunks, EMBEDDINGS).save_local(DB_PATH)
    return len(chunks)


@tool
def search_docs(query: str) -> str:
    """Search the ingested PDF for passages relevant to the query. Cite page numbers."""
    if not Path(DB_PATH).exists():
        return "No document has been ingested yet."
    vs = FAISS.load_local(DB_PATH, EMBEDDINGS, allow_dangerous_deserialization=True)
    hits = vs.similarity_search(query, k=4)
    if not hits:
        return "No relevant passages found."
    return "\n\n".join(
        f"[page {d.metadata.get('page', '?')}] {d.page_content}" for d in hits
    )
