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

