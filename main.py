"""
FastAPI application entry point.
"""
from fastapi import FastAPI
from database import Base, engine

# Import all models to register them with SQLAlchemy
from dao.models import File, Conversation, Message  # noqa: F401

app = FastAPI(
    title="Chat with PDF API",
    description="Hybrid-Inline PDF + RAG Chat System",
    version="0.1.0",
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Chat with PDF API"}

