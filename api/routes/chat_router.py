"""
Chat router for chat endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from services.chat_service.chat_handler import ChatHandler
from dao.chat_dao import ConversationDAO, MessageDAO
from api.schemas.request import ChatRequest
from api.schemas.response import (
    ChatResponse,
    ConversationResponse,
    ConversationListResponse,
    ConversationListItem,
    MessageItem,
    RetrievedChunk,
)
router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse, status_code=200)
async def chat(
    request: ChatRequest,
    session: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """
    Chat endpoint with inline PDF support.

    This endpoint processes chat messages and can associate PDF files with messages.
    If a file_id is provided and the file's ingestion_status is "uploaded", the PDF
    is downloaded from S3, converted to Base64, and sent to the LLM in inline mode.

    Args:
        request: ChatRequest containing message, optional conversation_id, and optional file_id
        session: Database session

    Returns:
        ChatResponse with assistant's response and metadata

    Raises:
        HTTPException: 400 if file_id is provided but file not found
    """
    chat_handler = ChatHandler()

    try:
        conversation, user_message, assistant_response, retrieval_mode, retrieved_chunks = (
            await chat_handler.process_chat(
                session=session,
                message=request.message,
                conversation_id=request.conversation_id,
                file_id=request.file_id,
            )
        )

        # Format retrieved chunks for response
        formatted_chunks = []
        if retrieved_chunks:
            for chunk in retrieved_chunks:
                formatted_chunks.append(
                    RetrievedChunk(
                        chunk_text=chunk.get("chunk_text", ""),
                        similarity_score=chunk.get("similarity_score", 0.0),
                    )
                )

        return ChatResponse(
            conversation_id=str(conversation.id),
            response=assistant_response,
            retrieval_mode=retrieval_mode,
            retrieved_chunks=formatted_chunks,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/chats", response_model=ConversationListResponse, status_code=200)
async def list_conversations(
    limit: int = Query(20, ge=1, le=100, description="Number of conversations to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_db),
) -> ConversationListResponse:
    """
    List all conversations with pagination.

    Args:
        limit: Maximum number of conversations to return (1-100)
        offset: Number of conversations to skip
        session: Database session

    Returns:
        ConversationListResponse with paginated list of conversations
    """
    conversation_dao = ConversationDAO()
    message_dao = MessageDAO()

    conversations, total = await conversation_dao.list(
        session=session, limit=limit, offset=offset
    )

    # Get message count for each conversation
    chat_items = []
    for conv in conversations:
        message_count = await message_dao.get_message_count_by_conversation(
            session, str(conv.id)
        )
        chat_items.append(
            ConversationListItem(
                conversation_id=str(conv.id),
                created_at=conv.created_at.isoformat(),
                message_count=message_count,
            )
        )

    return ConversationListResponse(
        chats=chat_items, total=total, limit=limit, offset=offset
    )


@router.get("/chats/{conversation_id}", response_model=ConversationResponse, status_code=200)
async def get_conversation(
    conversation_id: str,
    session: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """
    Get conversation details with all messages.

    Args:
        conversation_id: Conversation identifier (UUID)
        session: Database session

    Returns:
        ConversationResponse with conversation details and messages

    Raises:
        HTTPException: 404 if conversation not found
    """
    conversation_dao = ConversationDAO()
    message_dao = MessageDAO()

    conversation = await conversation_dao.get_by_id(session, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = await message_dao.get_by_conversation_id(session, conversation_id)

    message_items = []
    for msg in messages:
        retrieved_chunks = None
        if msg.retrieved_chunks:
            retrieved_chunks = [
                RetrievedChunk(**chunk) if isinstance(chunk, dict) else chunk
                for chunk in msg.retrieved_chunks
            ]

        message_items.append(
            MessageItem(
                role=msg.role.value,
                content=msg.content,
                file_id=str(msg.file_id) if msg.file_id else None,
                retrieval_mode=msg.retrieval_mode.value if msg.retrieval_mode else None,
                retrieved_chunks=retrieved_chunks,
                created_at=msg.created_at.isoformat(),
            )
        )

    return ConversationResponse(
        conversation_id=str(conversation.id),
        created_at=conversation.created_at.isoformat(),
        messages=message_items,
    )

