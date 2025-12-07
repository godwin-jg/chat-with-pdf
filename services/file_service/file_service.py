"""
File service for file management operations.
"""
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from dao.file_dao import FileDAO
from dao.models.file import File, IngestionStatus
from core.aws.s3_client import get_s3_client


class FileService:
    """Service for file management operations."""

    def __init__(self):
        """Initialize file service."""
        self.file_dao = FileDAO()
        self.s3_client = get_s3_client()

    async def get_file_by_id(
        self, session: AsyncSession, file_id: str
    ) -> Optional[File]:
        """
        Get a file by ID.

        Args:
            session: Database session
            file_id: File ID (UUID string)

        Returns:
            File instance or None if not found
        """
        return await self.file_dao.get_by_id(session, file_id)

    async def list_files(
        self,
        session: AsyncSession,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[File], int]:
        """
        List all files with pagination.

        Args:
            session: Database session
            limit: Maximum number of files to return
            offset: Number of files to skip

        Returns:
            Tuple of (list of files, total count)
        """
        return await self.file_dao.list(session, limit=limit, offset=offset)

    async def get_file_with_download_url(
        self, session: AsyncSession, file_id: str, expires_in: int = 3600
    ) -> Optional[dict]:
        """
        Get file details with presigned download URL.

        Args:
            session: Database session
            file_id: File ID (UUID string)
            expires_in: Download URL expiration in seconds

        Returns:
            Dictionary with file details and download URL, or None if not found
        """
        file = await self.file_dao.get_by_id(session, file_id)
        if not file:
            return None

        download_url = self.s3_client.generate_presigned_url(
            s3_key=file.s3_key, expires_in=expires_in
        )

        return {
            "file_id": str(file.id),
            "s3_key": file.s3_key,
            "ingestion_status": file.ingestion_status.value,
            "presigned_download_url": download_url,
            "download_url_expires_in_seconds": expires_in,
            "created_at": file.created_at.isoformat(),
            "updated_at": file.updated_at.isoformat(),
        }

