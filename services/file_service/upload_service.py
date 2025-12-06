"""
File upload service for presigned URL generation.
"""
import uuid
from typing import Dict
from core.aws.s3_client import get_s3_client


class UploadService:
    """Service for handling file uploads."""

    def __init__(self):
        """Initialize upload service."""
        self.s3_client = get_s3_client()

    def generate_presigned_upload(
        self, filename: str, expires_in: int = 3600
    ) -> Dict[str, any]:
        """
        Generate a presigned URL for file upload.

        This method generates a unique file_id and creates a presigned PUT URL
        for uploading the file to S3. The file record is NOT created in the
        database at this point - it will be created by the webhook when the
        file is actually uploaded to S3.

        Args:
            filename: Original filename (for reference, not used in S3 key)
            expires_in: Expiration time in seconds (default: 1 hour)

        Returns:
            Dictionary containing:
                - file_id: Unique file identifier (UUID)
                - presigned_url: Presigned PUT URL
                - expires_in_seconds: Expiration time
        """
        # Generate unique file_id
        file_id = str(uuid.uuid4())

        # Generate presigned PUT URL
        presigned_url = self.s3_client.generate_presigned_upload_url(
            file_id=file_id, expires_in=expires_in
        )

        return {
            "file_id": file_id,
            "presigned_url": presigned_url,
            "expires_in_seconds": expires_in,
        }

