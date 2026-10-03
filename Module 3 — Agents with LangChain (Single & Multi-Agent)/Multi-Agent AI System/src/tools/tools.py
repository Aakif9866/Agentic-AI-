"""Tools the agents can call: web search (Tavily) and page scraping (requests + BeautifulSoup)."""

import requests
from bs4 import BeautifulSoup
from dotenv import find_dotenv, load_dotenv
from langchain.tools import tool
from langchain_tavily import TavilySearch

# Loaded here because this is the first module imported, and TavilySearch reads its key on creation.
load_dotenv(find_dotenv(usecwd=True))

# ==========================================
# CONFIG
# ==========================================

MAX_PAGE_CHARS = 4000  # keeps scraped text under Groq's free 8k tokens/min
HEADERS = {"User-Agent": "Mozilla/5.0 (research-assistant)"}  # some sites block requests' default UA


# ==========================================
# TOOLS
# ==========================================

# Ready-made tool: already a LangChain tool, nothing to wrap.
web_search = TavilySearch(max_results=3)


@tool
def scrape_url(url: str) -> str:
    """Download a web page and return its main readable text. Use this to read a URL in depth."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        return f"Could not fetch {url}: {e}"

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
        tag.decompose()  # drop page chrome, keep the article

    text = " ".join(soup.get_text(separator=" ").split())  # collapse whitespace
    if not text:
        return f"No readable text found at {url}."
    return text[:MAX_PAGE_CHARS]
