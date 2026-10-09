"""The four workers of the pipeline.

Agents (LLM + tools, decide their own steps):  search agent, reader agent
Chains (LLM only, one fixed step):             writer chain, critic chain
"""

from groq import BadRequestError
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from src.tools.tools import scrape_url, web_search

# ==========================================
# CONFIG
# ==========================================

MODEL = "groq:openai/gpt-oss-120b"
MAX_STEPS = 15  # recursion_limit (each tool call = 2 steps): stops an agent looping forever
ON_ERROR = "If a tool returns an error, tell the user instead of retrying."

# gpt-oss on Groq sometimes emits a malformed tool call -> 400 "tool_use_failed". It's random, so rerun.
RETRY = {"retry_if_exception_type": (BadRequestError,), "stop_after_attempt": 3}

llm = init_chat_model(MODEL, temperature=0.3, max_retries=5)  # retries ride out Groq 429s


# ==========================================
# AGENTS (have tools)
# ==========================================

def build_search_agent():
    return create_agent(
        llm,
        tools=[web_search],
        system_prompt=(
            "You are a research search specialist. Use AT MOST 2 searches, then "
            "summarise the key facts, figures and dates you found. List every source URL "
            f"you used at the end. {ON_ERROR}"
        ),
    ).with_config({"recursion_limit": MAX_STEPS}).with_retry(**RETRY)


def build_reader_agent():
    return create_agent(
        llm,
        tools=[scrape_url],
        system_prompt=(
            "You are a research reader. Pick the single most relevant URL you are given, "
            "scrape it, and extract the important details, facts and quotes in a structured "
            f"summary. {ON_ERROR}"
        ),
    ).with_config({"recursion_limit": MAX_STEPS}).with_retry(**RETRY)


# ==========================================
# CHAINS (no tools): prompt | llm | parser
# ==========================================

writer_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are an expert research writer. Write a clear, well-structured report in Markdown "
     "with: Title, Executive Summary, Key Findings, Analysis, Conclusion, Sources. "
     "Use only the research provided; do not invent facts."),
    ("user", "Topic: {topic}\n\nResearch:\n{research}"),
])

critic_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a strict research critic. Review the report and reply in Markdown with: "
     "Score (x/10), Strengths, Weaknesses, Suggestions. Be specific and brief."),
    ("user", "Report:\n{report}"),
])

writer_chain = writer_prompt | llm | StrOutputParser()
critic_chain = critic_prompt | llm | StrOutputParser()
