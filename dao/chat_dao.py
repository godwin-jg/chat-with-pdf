"""
Chat DAO for conversation and message operations.
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from dao.base_dao import BaseDAO
from dao.models.conversation import Conversation
from dao.models.message import Message, MessageRole, RetrievalMode


class ConversationDAO(BaseDAO[Conversation]):
    """DAO for conversation operations."""

    def __init__(self):
        """Initialize ConversationDAO."""
        super().__init__(Conversation)


class MessageDAO(BaseDAO[Message]):
    """DAO for message operations."""

    def __init__(self):
        """Initialize MessageDAO."""
        super().__init__(Message)

    async def get_by_conversation_id(
        self, session: AsyncSession, conversation_id: str, order_by_created: bool = True
    ) -> List[Message]:
        """
        Get all messages for a conversation.

        Args:
            session: Database session
            conversation_id: Conversation ID (UUID string)
            order_by_created: If True, order by created_at ascending

        Returns:
            List of messages
        """
        query = select(Message).where(Message.conversation_id == conversation_id)

        if order_by_created:
            query = query.order_by(Message.created_at.asc())

        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_message_count_by_conversation(
        self, session: AsyncSession, conversation_id: str
    ) -> int:
        """
        Get message count for a conversation.

        Args:
            session: Database session
            conversation_id: Conversation ID (UUID string)

        Returns:
            Number of messages
        """
        query = select(func.count()).select_from(Message).where(
            Message.conversation_id == conversation_id
        )
        result = await session.execute(query)
        return result.scalar() or 0

