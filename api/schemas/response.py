"""
Pydantic response schemas for API endpoints.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class PresignResponse(BaseModel):
    """Response schema for presigned URL generation."""

    file_id: str = Field(..., description="Unique file identifier (UUID)")
    presigned_url: str = Field(..., description="Presigned PUT URL for uploading")
    expires_in_seconds: int = Field(..., description="URL expiration time in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "file_id": "123e4567-e89b-12d3-a456-426614174000",
                "presigned_url": "https://s3.amazonaws.com/bucket/...",
                "expires_in_seconds": 3600,
            }
        }


class FileResponse(BaseModel):
    """Response schema for file details."""

    file_id: str = Field(..., description="File identifier (UUID)")
    s3_key: str = Field(..., description="S3 object key")
    ingestion_status: str = Field(..., description="Ingestion status")
    presigned_download_url: Optional[str] = Field(
        None, description="Presigned download URL (if requested)"
    )
    download_url_expires_in_seconds: Optional[int] = Field(
        None, description="Download URL expiration time"
    )
    created_at: str = Field(..., description="Creation timestamp (ISO format)")
    updated_at: str = Field(..., description="Last update timestamp (ISO format)")

    class Config:
        json_schema_extra = {
            "example": {
                "file_id": "123e4567-e89b-12d3-a456-426614174000",
                "s3_key": "uploads/123e4567-e89b-12d3-a456-426614174000.pdf",
                "ingestion_status": "uploaded",
                "presigned_download_url": "https://s3.amazonaws.com/...",
                "download_url_expires_in_seconds": 3600,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        }


class FileListItem(BaseModel):
    """Schema for file list item."""

    file_id: str = Field(..., description="File identifier (UUID)")
    s3_key: str = Field(..., description="S3 object key")
    ingestion_status: str = Field(..., description="Ingestion status")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")
    updated_at: str = Field(..., description="Last update timestamp (ISO format)")

    class Config:
        json_schema_extra = {
            "example": {
                "file_id": "123e4567-e89b-12d3-a456-426614174000",
                "s3_key": "uploads/123e4567-e89b-12d3-a456-426614174000.pdf",
                "ingestion_status": "uploaded",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        }


class FileListResponse(BaseModel):
    """Response schema for file list endpoint."""

    files: List[FileListItem] = Field(..., description="List of files")
    total: int = Field(..., description="Total number of files")
    limit: int = Field(..., description="Pagination limit")
    offset: int = Field(..., description="Pagination offset")

    class Config:
        json_schema_extra = {
            "example": {
                "files": [
                    {
                        "file_id": "123e4567-e89b-12d3-a456-426614174000",
                        "s3_key": "uploads/123e4567-e89b-12d3-a456-426614174000.pdf",
                        "ingestion_status": "uploaded",
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                    }
                ],
                "total": 15,
                "limit": 20,
                "offset": 0,
            }
        }


class WebhookIngestResponse(BaseModel):
    """Response schema for webhook ingestion endpoint."""

    file_id: str = Field(..., description="File identifier (UUID)")
    s3_key: str = Field(..., description="S3 object key")
    ingestion_status: str = Field(..., description="Ingestion status")
    message: str = Field(..., description="Status message")

    class Config:
        json_schema_extra = {
            "example": {
                "file_id": "123e4567-e89b-12d3-a456-426614174000",
                "s3_key": "uploads/123e4567-e89b-12d3-a456-426614174000.pdf",
                "ingestion_status": "uploaded",
                "message": "File record created successfully",
            }
        }


class RetrievedChunk(BaseModel):
    """Schema for a retrieved chunk."""

    chunk_text: str = Field(..., description="Chunk text content")
    similarity_score: Optional[float] = Field(None, description="Similarity score")

    class Config:
        json_schema_extra = {
            "example": {
                "chunk_text": "This is a relevant chunk of text...",
                "similarity_score": 0.92,
            }
        }


class ChatResponse(BaseModel):
    """Response schema for chat endpoint."""

    conversation_id: str = Field(..., description="Conversation identifier (UUID)")
    response: str = Field(..., description="Assistant's response")
    retrieval_mode: str = Field(..., description="Retrieval mode used (inline or rag)")
    retrieved_chunks: List[RetrievedChunk] = Field(
        default_factory=list, description="Retrieved chunks (empty for inline mode)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
                "response": "The document discusses...",
                "retrieval_mode": "inline",
                "retrieved_chunks": [],
            }
        }


class MessageItem(BaseModel):
    """Schema for a message in conversation history."""

    role: str = Field(..., description="Message role (user or assistant)")
    content: str = Field(..., description="Message content")
    file_id: Optional[str] = Field(None, description="Associated file ID (if any)")
    retrieval_mode: Optional[str] = Field(
        None, description="Retrieval mode (inline or rag)"
    )
    retrieved_chunks: Optional[List[RetrievedChunk]] = Field(
        None, description="Retrieved chunks (if any)"
    )
    created_at: str = Field(..., description="Creation timestamp (ISO format)")

    class Config:
        json_schema_extra = {
            "example": {
                "role": "user",
                "content": "What is this document about?",
                "file_id": "123e4567-e89b-12d3-a456-426614174000",
                "retrieval_mode": None,
                "retrieved_chunks": None,
                "created_at": "2024-01-01T00:00:00Z",
            }
        }


class ConversationResponse(BaseModel):
    """Response schema for conversation details."""

    conversation_id: str = Field(..., description="Conversation identifier (UUID)")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")
    messages: List[MessageItem] = Field(..., description="List of messages")

    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
                "created_at": "2024-01-01T00:00:00Z",
                "messages": [
                    {
                        "role": "user",
                        "content": "What is this document about?",
                        "file_id": "123e4567-e89b-12d3-a456-426614174000",
                        "retrieval_mode": None,
                        "retrieved_chunks": None,
                        "created_at": "2024-01-01T00:00:00Z",
                    }
                ],
            }
        }


class ConversationListItem(BaseModel):
    """Schema for conversation list item."""

    conversation_id: str = Field(..., description="Conversation identifier (UUID)")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")
    message_count: int = Field(..., description="Number of messages in conversation")

    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
                "created_at": "2024-01-01T00:00:00Z",
                "message_count": 5,
            }
        }


class ConversationListResponse(BaseModel):
    """Response schema for conversation list endpoint."""

    chats: List[ConversationListItem] = Field(..., description="List of conversations")
    total: int = Field(..., description="Total number of conversations")
    limit: int = Field(..., description="Pagination limit")
    offset: int = Field(..., description="Pagination offset")

    class Config:
        json_schema_extra = {
            "example": {
                "chats": [
                    {
                        "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
                        "created_at": "2024-01-01T00:00:00Z",
                        "message_count": 5,
                    }
                ],
                "total": 42,
                "limit": 20,
                "offset": 0,
            }
        }


class RetrieveResultItem(BaseModel):
    """Schema for a single retrieve result item."""

    chunk_id: str = Field(..., description="Chunk identifier")
    file_id: str = Field(..., description="File ID this chunk belongs to")
    chunk_text: str = Field(..., description="Chunk text content")
    similarity_score: float = Field(..., description="Similarity score")

    class Config:
        json_schema_extra = {
            "example": {
                "chunk_id": "123e4567-e89b-12d3-a456-426614174000-chunk-0",
                "file_id": "123e4567-e89b-12d3-a456-426614174000",
                "chunk_text": "This is a relevant chunk of text...",
                "similarity_score": 0.92,
            }
        }


class RetrieveResponse(BaseModel):
    """Response schema for retrieve endpoint."""

    results: List[RetrieveResultItem] = Field(..., description="List of retrieved chunks")

    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "chunk_id": "123e4567-e89b-12d3-a456-426614174000-chunk-0",
                        "file_id": "123e4567-e89b-12d3-a456-426614174000",
                        "chunk_text": "This is a relevant chunk...",
                        "similarity_score": 0.92,
                    }
                ],
            }
        }

