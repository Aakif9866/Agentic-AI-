"""Single AI Agent: a Streamlit chat app with web search and weather tools.

Run from the project root:
    uv run streamlit run project/app.py
"""

import os

import requests
import streamlit as st
from dotenv import find_dotenv, load_dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.messages import AIMessage, ToolMessage
from langchain_tavily import TavilySearch

load_dotenv(find_dotenv(usecwd=True))

# ==========================================
# CONFIG
# ==========================================

MODELS = {
    "Groq - gpt-oss-120b (free)": ("groq:openai/gpt-oss-120b", "GROQ_API_KEY"),
    "OpenAI - gpt-4o-mini": ("openai:gpt-4o-mini", "OPENAI_API_KEY"),
}
SYSTEM_PROMPT = "You are a helpful assistant. Use tools for current facts. If a tool returns an error, tell the user instead of retrying. Be concise."
MAX_STEPS = 10  # stops a confused agent from looping forever


# ==========================================
# TOOLS
# ==========================================

@tool
def get_weather_data(city: str) -> str:
    """Get the current weather (temperature, conditions, humidity) for a city."""
    try:
        response = requests.get(
            "https://api.weatherstack.com/current",
            params={"access_key": os.getenv("WEATHERSTACK_API_KEY"), "query": city},
            timeout=10,
        )
        data = response.json()
    except requests.RequestException as e:
        return f"Weather service error: {e}"

    if "current" not in data:
        error = data.get("error", {}).get("info", "unknown error")
        return f"Could not fetch weather data for {city}: {error}"

    current = data["current"]
    return (
        f"City: {city}\n"
        f"Temperature: {current['temperature']}°C\n"
        f"Weather: {current['weather_descriptions'][0]}\n"
        f"Humidity: {current['humidity']}%"
    )


# ==========================================
# AGENT
# ==========================================

@st.cache_resource
def build_agent(model: str):
    """Build once per model; Streamlit reruns the script on every interaction."""
    return create_agent(
        model,
        tools=[TavilySearch(max_results=2), get_weather_data],
        system_prompt=SYSTEM_PROMPT,
    )


# ==========================================
# UI
# ==========================================

st.set_page_config(page_title="Single AI Agent", page_icon="🤖")
st.title("🤖 Single AI Agent")
st.caption("An LLM that can search the web and check the weather.")

with st.sidebar:
    st.header("Settings")
    model_label = st.selectbox("Model", list(MODELS))
    model, model_key = MODELS[model_label]

    st.subheader("API keys")
    for key in (model_key, "TAVILY_API_KEY", "WEATHERSTACK_API_KEY"):
        st.write(f"{'✅' if os.getenv(key) else '❌'} `{key}`")

    if st.button("Clear chat"):
        st.session_state.messages = []

missing = [k for k in (model_key, "TAVILY_API_KEY") if not os.getenv(k)]
if missing:
    st.error(f"Add {', '.join(missing)} to your .env file, then restart the app.")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []  # [{"role": "user" | "assistant", "content": str}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).markdown(msg["content"])

if question := st.chat_input("e.g. Find the capital of India and its current weather"):
    st.session_state.messages.append({"role": "user", "content": question})
    st.chat_message("user").markdown(question)

    agent = build_agent(model)
    history = [(m["role"], m["content"]) for m in st.session_state.messages]

    with st.chat_message("assistant"):
        answer = ""
        with st.status("Thinking...", expanded=False) as status:
            try:
                for update in agent.stream(
                    {"messages": history},
                    {"recursion_limit": MAX_STEPS * 2},
                    stream_mode="updates",
                ):
                    for msg in next(iter(update.values()))["messages"]:
                        if isinstance(msg, AIMessage) and msg.tool_calls:
                            for call in msg.tool_calls:
                                st.write(f"🔧 **{call['name']}** `{call['args']}`")
                        elif isinstance(msg, ToolMessage):
                            st.code(str(msg.content)[:500], language=None)
                        elif isinstance(msg, AIMessage):
                            answer = msg.content
                status.update(label="Done", state="complete")
            except Exception as e:
                status.update(label="Error", state="error")
                answer = f"⚠️ {e}"
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
