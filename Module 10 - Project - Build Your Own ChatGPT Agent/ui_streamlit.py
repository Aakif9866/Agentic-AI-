"""Optional local UI:  uv run streamlit run ui_streamlit.py

Talks to the graph directly (not through the API), so you can see memory,
threads, streaming and approval working without running two processes.
"""
import uuid
import streamlit as st
from langchain_core.messages import AIMessageChunk
from langgraph.types import Command

from backend import agent, all_thread_ids, pending_approval

st.set_page_config(page_title="My ChatGPT Agent", page_icon="*")

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

with st.sidebar:
    st.header("Threads")
    if st.button("New chat"):
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()
    for t in all_thread_ids():
        if st.button(t[:8], key=t):
            st.session_state.thread_id = t
            st.rerun()
    st.caption(f"Active: {st.session_state.thread_id[:8]}")

cfg = {"configurable": {"thread_id": st.session_state.thread_id}}

for m in agent.get_state(cfg).values.get("messages", []):
    if m.type in ("human", "ai") and m.content:
        st.chat_message("user" if m.type == "human" else "assistant").write(m.content)

# If the agent paused for approval, show the draft instead of a chat box.
draft = pending_approval(st.session_state.thread_id)
if draft:
    st.warning(f"Approval needed: {draft['action']} to {draft['to']}")
    edited = st.text_area("Body (you can edit before sending)", draft["body"], height=200)
    col1, col2 = st.columns(2)
    if col1.button("Approve & send", type="primary"):
        agent.invoke(Command(resume={"approved": True, "edited_body": edited}), cfg)
        st.rerun()
    if col2.button("Reject"):
        agent.invoke(Command(resume={"approved": False}), cfg)
        st.rerun()
else:
    if prompt := st.chat_input("Ask anything"):
        st.chat_message("user").write(prompt)
        with st.chat_message("assistant"):
            box = st.empty()
            acc = ""
            for chunk, _meta in agent.stream(
                {"messages": [("user", prompt)]}, cfg, stream_mode="messages"
            ):
                if isinstance(chunk, AIMessageChunk) and chunk.content:
                    acc += chunk.content
                    box.markdown(acc)
        st.rerun()
