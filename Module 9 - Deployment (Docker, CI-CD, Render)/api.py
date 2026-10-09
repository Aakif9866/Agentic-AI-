from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import AIMessageChunk

from backend import agent, all_thread_ids

app = FastAPI(title="Agentic Chatbot API")


class ChatIn(BaseModel):
    thread_id: str
    message: str


@app.post("/chat")
def chat(body: ChatIn):
    """Stream the reply token by token, so a UI can render it as it arrives."""
    cfg = {"configurable": {"thread_id": body.thread_id}}

    def token_stream():
        for chunk, _meta in agent.stream(
            {"messages": [("user", body.message)]}, cfg, stream_mode="messages"
        ):
            if isinstance(chunk, AIMessageChunk) and chunk.content:
                yield chunk.content

    return StreamingResponse(token_stream(), media_type="text/plain")


@app.get("/threads")
def threads():
    return {"thread_ids": all_thread_ids()}


@app.get("/health")
def health():
    """Render and the CI smoke test both poll this."""
    return {"ok": True}
