"""
FastAPI application entry point.
"""
from fastapi import FastAPI

# Import all models to register them with SQLAlchemy
from dao.models import File, Conversation, Message  # noqa: F401

# Import routers
from api.routes import file_router, webhook_router, chat_router, retrieve_router

app = FastAPI(
    title="Chat with PDF API",
    description="Hybrid-Inline PDF + RAG Chat System",
    version="0.1.0",
)

# Include routers
app.include_router(file_router.router)
app.include_router(webhook_router.router)
app.include_router(chat_router.router)
app.include_router(retrieve_router.router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Chat with PDF API"}


@app.get("/debug/models")
async def debug_models():
    """Debug endpoint to check available OpenAI models."""
    try:
        from core.openai.openai_client import get_openai_client
        client = get_openai_client()
        
        # Try to list models
        try:
            models = client.client.models.list()
            available = [model.id for model in models.data]
            return {
                "status": "success",
                "available_models": available,
                "total": len(available),
                "current_model": client.model,
            }
        except Exception as e:
            # Try testing a few models directly
            test_models = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
            working = []
            for model in test_models:
                try:
                    response = client.client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": "test"}],
                        max_tokens=1
                    )
                    working.append(model)
                except:
                    pass
            
            return {
                "status": "partial",
                "working_models": working,
                "error": str(e)[:200],
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}

