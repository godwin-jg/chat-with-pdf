"""
Conversation model for storing chat conversations.
"""
from dao.models.base import BaseModel


class Conversation(BaseModel):
    """Model representing a conversation."""

    __tablename__ = "conversations"

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, created_at={self.created_at})>"

