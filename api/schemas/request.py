"""
Pydantic request schemas for API endpoints.
"""
from pydantic import BaseModel, Field
from typing import Optional


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

