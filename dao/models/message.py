"""
Message model for storing chat messages.
"""
from sqlalchemy import Column, String, Enum, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from dao.models.base import BaseModel


class MessageRole(str, enum.Enum):
    """Enumeration for message roles."""

    USER = "user"
    ASSISTANT = "assistant"


class RetrievalMode(str, enum.Enum):
    """Enumeration for retrieval modes."""

    INLINE = "inline"
    RAG = "rag"


class Message(BaseModel):
    """Model representing a chat message."""

    __tablename__ = "messages"

    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(Enum(MessageRole, values_callable=lambda x: [e.value for e in x], native_enum=False, length=20), nullable=False)
    content = Column(Text, nullable=False)
    file_id = Column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    retrieval_mode = Column(Enum(RetrievalMode, values_callable=lambda x: [e.value for e in x], native_enum=False, length=20), nullable=True)
    retrieved_chunks = Column(JSON, nullable=True)

    # Relationships
    conversation = relationship("Conversation", backref="messages")
    file = relationship("File", backref="messages")

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, role={self.role}, conversation_id={self.conversation_id})>"

