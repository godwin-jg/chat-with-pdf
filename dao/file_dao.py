"""
File DAO for file-related database operations.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dao.base_dao import BaseDAO
from dao.models.file import File, IngestionStatus


class FileDAO(BaseDAO[File]):
    """DAO for file operations."""

    def __init__(self):
        """Initialize FileDAO."""
        super().__init__(File)

    async def get_by_s3_key(
        self, session: AsyncSession, s3_key: str
    ) -> Optional[File]:
        """
        Get a file by S3 key.

        Args:
            session: Database session
            s3_key: S3 object key

        Returns:
            File instance or None if not found
        """
        query = select(File).where(File.s3_key == s3_key)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_file_id(
        self, session: AsyncSession, file_id: str
    ) -> Optional[File]:
        """
        Get a file by file_id (extracted from S3 key).

        Args:
            session: Database session
            file_id: File ID (UUID string)

        Returns:
            File instance or None if not found
        """
        s3_key = f"uploads/{file_id}.pdf"
        return await self.get_by_s3_key(session, s3_key)

    async def update_status(
        self,
        session: AsyncSession,
        file_id: str,
        status: IngestionStatus,
    ) -> Optional[File]:
        """
        Update file ingestion status.

        Args:
            session: Database session
            file_id: File ID (UUID string)
            status: New ingestion status

        Returns:
            Updated file instance or None if not found
        """
        return await self.update(session, file_id, ingestion_status=status)

