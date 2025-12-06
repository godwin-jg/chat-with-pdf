"""
File ingestion service for processing uploaded files.
"""
import re
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from dao.file_dao import FileDAO
from dao.models.file import File, IngestionStatus
from core.aws.s3_client import get_s3_client


class IngestionService:
    """Service for handling file ingestion from S3 events."""

    def __init__(self):
        """Initialize ingestion service."""
        self.file_dao = FileDAO()
        self.s3_client = get_s3_client()

    def extract_file_id_from_s3_key(self, s3_key: str) -> Optional[str]:
        """
        Extract file_id from S3 key.

        S3 key format: uploads/{file_id}.pdf

        Args:
            s3_key: S3 object key

        Returns:
            File ID (UUID string) or None if format is invalid
        """
        # Match pattern: uploads/{uuid}.pdf
        pattern = r"^uploads/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})\.pdf$"
        match = re.match(pattern, s3_key)
        if match:
            return match.group(1)
        return None

    async def create_file_from_s3_event(
        self, session: AsyncSession, s3_bucket: str, s3_key: str
    ) -> Optional[File]:
        """
        Create a file record from an S3 upload event.

        This is called by the webhook when a file is uploaded to S3.
        It extracts the file_id from the S3 key and creates a file record
        with status "uploaded".

        Args:
            session: Database session
            s3_bucket: S3 bucket name
            s3_key: S3 object key (format: uploads/{file_id}.pdf)

        Returns:
            Created File instance or None if file_id extraction fails
        """
        # Extract file_id from S3 key
        file_id = self.extract_file_id_from_s3_key(s3_key)
        if not file_id:
            return None

        # Check if file already exists
        existing_file = await self.file_dao.get_by_s3_key(session, s3_key)
        if existing_file:
            return existing_file

        # Create new file record with status "uploaded"
        # Convert file_id string to UUID
        file_uuid = uuid.UUID(file_id)
        file = await self.file_dao.create(
            session,
            id=file_uuid,  # Use the extracted file_id as the primary key
            s3_key=s3_key,
            ingestion_status=IngestionStatus.UPLOADED,
        )

        return file

