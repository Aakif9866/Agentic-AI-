"""Every tool the agent can call. One place, so backend.py stays short."""
import re
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langgraph.types import interrupt

# TavilySearch reads its key at construction time (below), so load .env here rather
# than relying on whoever imports this module having done it first.
load_dotenv()

import os

# Embeddings are swappable too, but note the dimensions differ (MiniLM 384 vs
# OpenAI 1536), so changing this REQUIRES re-running ingest.py. See ../OpenAI.md.
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

if EMBED_MODEL.startswith("text-embedding-"):
    from langchain_openai import OpenAIEmbeddings

    EMBEDDINGS = OpenAIEmbeddings(model=EMBED_MODEL)
else:
    EMBEDDINGS = HuggingFaceEmbeddings(model_name=EMBED_MODEL)

DB_PATH = "faiss_db"

# Whitelist instead of a bare eval(): the expression comes from an LLM, which means it
# is not fully trusted input. No names can appear, so no attribute tricks are possible.
SAFE_EXPR = re.compile(r"[0-9.\s+\-*/%()]+")


def ingest_pdf(pdf_path: str) -> int:
    """Chunk + embed a PDF so `search_docs` can find things in it."""
    docs = PyPDFLoader(pdf_path).load()
    for d in docs:
        d.page_content = " ".join(d.page_content.split())
    chunks = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=80).split_documents(docs)
    FAISS.from_documents(chunks, EMBEDDINGS).save_local(DB_PATH)
    return len(chunks)


@tool
def calculator(expression: str) -> str:
    """Evaluate an arithmetic expression. Numbers and + - * / % ( ) ** only, e.g. '2**10'."""
    if not SAFE_EXPR.fullmatch(expression):
        return "error: only numbers and + - * / % ( ) are allowed"
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"error: {e}"


web_search = TavilySearch(max_results=3)


@tool
def search_docs(query: str) -> str:
    """Search the user's uploaded PDF for relevant passages. Cite page numbers."""
    if not Path(DB_PATH).exists():
        return "No document has been uploaded yet."
    vs = FAISS.load_local(DB_PATH, EMBEDDINGS, allow_dangerous_deserialization=True)
    hits = vs.similarity_search(query, k=4)
    if not hits:
        return "No relevant passages found."
    return "\n\n".join(f"[page {d.metadata.get('page', '?')}] {d.page_content}" for d in hits)


@tool
def send_email(to: str, subject: str, body: str) -> dict:
    """Send an email. ALWAYS requires human approval before sending."""
    decision = interrupt({"action": "send_email", "to": to, "subject": subject, "body": body})
    if decision.get("approved"):
        return {
            "status": "sent",
            "to": to,
            "subject": subject,
            "body": decision.get("edited_body", body),
        }
    return {"status": "cancelled"}


ALL_TOOLS = [calculator, web_search, search_docs, send_email]
