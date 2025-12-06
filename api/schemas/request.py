"""
Pydantic request schemas for API endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class PresignRequest(BaseModel):
    """Request schema for presigned URL generation."""

    filename: str = Field(..., description="Original filename", min_length=1)

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "document.pdf",
            }
        }


class WebhookIngestRequest(BaseModel):
    """Request schema for webhook ingestion endpoint."""

    s3_bucket: str = Field(..., description="S3 bucket name")
    s3_key: str = Field(..., description="S3 object key (e.g., uploads/{file_id}.pdf)")

    class Config:
        json_schema_extra = {
            "example": {
                "s3_bucket": "swe-test-godwin-j",
                "s3_key": "uploads/123e4567-e89b-12d3-a456-426614174000.pdf",
            }
        }


class ChatRequest(BaseModel):
    """Request schema for chat endpoint."""

    message: str = Field(..., description="User's message", min_length=1)
    conversation_id: Optional[str] = Field(
        None, description="Conversation ID (creates new if not provided)"
    )
    file_id: Optional[str] = Field(
        None, description="File ID to associate with this message (optional)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": "What is this document about?",
                "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
                "file_id": "123e4567-e89b-12d3-a456-426614174000",
            }
        }


class RetrieveRequest(BaseModel):
    """Request schema for retrieve endpoint."""

    file_ids: List[str] = Field(
        ..., description="List of file IDs to search in", min_items=1
    )
    query: str = Field(..., description="Search query", min_length=1)
    top_k: int = Field(5, description="Number of top results to return", ge=1, le=20)

    class Config:
        json_schema_extra = {
            "example": {
                "file_ids": ["123e4567-e89b-12d3-a456-426614174000"],
                "query": "What is the main topic?",
                "top_k": 5,
            }
        }
