from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import AIMessageChunk
from langgraph.types import Command

from backend import agent, all_thread_ids, pending_approval

app = FastAPI(title="ChatGPT-style Agent (Modules 6-9 combined)")


class ChatIn(BaseModel):
    thread_id: str
    message: str


class ApproveIn(BaseModel):
    thread_id: str
    approved: bool
    edited_body: str | None = None


@app.post("/chat")
def chat(body: ChatIn):
    cfg = {"configurable": {"thread_id": body.thread_id}}

    def token_stream():
        for chunk, _meta in agent.stream(
            {"messages": [("user", body.message)]}, cfg, stream_mode="messages"
        ):
            if isinstance(chunk, AIMessageChunk) and chunk.content:
                yield chunk.content

    return StreamingResponse(token_stream(), media_type="text/plain")


@app.get("/pending/{thread_id}")
def pending(thread_id: str):
    """Poll this to find out whether the agent is waiting on a human."""
    return {"pending": pending_approval(thread_id)}


@app.post("/approve")
def approve(body: ApproveIn):
    """Resume a paused thread. edited_body lets the human change the draft first."""
    cfg = {"configurable": {"thread_id": body.thread_id}}
    resume_value: dict = {"approved": body.approved}
    if body.edited_body:
        resume_value["edited_body"] = body.edited_body
    result = agent.invoke(Command(resume=resume_value), cfg)
    return {"final_message": result["messages"][-1].content}


@app.get("/threads")
def threads():
    return {"thread_ids": all_thread_ids()}


@app.get("/health")
def health():
    return {"ok": True}
