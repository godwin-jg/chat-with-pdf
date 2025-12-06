"""
FastAPI application entry point.
"""
from fastapi import FastAPI
from database import Base

# Import all models to register them with SQLAlchemy
from dao.models import File, Conversation, Message  # noqa: F401

# Import routers
from api.routes import file_router, webhook_router

app = FastAPI(
    title="Chat with PDF API",
    description="Hybrid-Inline PDF + RAG Chat System",
    version="0.1.0",
)

# Include routers
app.include_router(file_router.router)
app.include_router(webhook_router.router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Chat with PDF API"}

