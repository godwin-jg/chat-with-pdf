"""
File ingestion service for processing uploaded files.
"""
import re
import uuid
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from dao.file_dao import FileDAO
from dao.models.file import File, IngestionStatus
from core.aws.s3_client import get_s3_client
from core.parsers.pdf_parser import extract_text_from_pdf
from core.chunker.text_chunker import chunk_text
from core.openai.openai_client import get_openai_client
from core.vector.upstash_client import get_upstash_client

logger = logging.getLogger(__name__)


class IngestionService:
    """Service for handling file ingestion from S3 events."""

    def __init__(self):
        """Initialize ingestion service."""
        self.file_dao = FileDAO()
        self.s3_client = get_s3_client()
        self.openai_client = get_openai_client()
        self.upstash_client = get_upstash_client()

    def extract_file_id_from_s3_key(self, s3_key: str) -> Optional[str]:
        """Extract file_id from S3 key."""
        pattern = r"^uploads/([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})\.pdf$"
        match = re.match(pattern, s3_key)
        if match:
            return match.group(1)
        return None

    def _sanitize_text(self, text: str) -> str:
        """Remove null bytes and non-printable characters."""
        if not text:
            return ""
        text = text.replace('\x00', '')
        text = "".join(ch for ch in text if ch.isprintable() or ch in ['\n', '\t', '\r', ' '])
        return text.encode('utf-8', 'ignore').decode('utf-8')

    async def create_file_from_s3_event(
        self, session: AsyncSession, s3_bucket: str, s3_key: str
    ) -> Optional[File]:
        """Create a file record from an S3 upload event."""
        file_id = self.extract_file_id_from_s3_key(s3_key)
        if not file_id:
            return None

        existing_file = await self.file_dao.get_by_s3_key(session, s3_key)
        if existing_file:
            return existing_file

        file_uuid = uuid.UUID(file_id)
        file = await self.file_dao.create(
            session,
            id=file_uuid,
            s3_key=s3_key,
            ingestion_status=IngestionStatus.UPLOADED,
        )

        return file

    async def process_file_ingestion(
        self, session: AsyncSession, file_id: str
    ) -> None:
        """Process full file ingestion pipeline."""
        try:
            file = await self.file_dao.get_by_id(session, file_id)
            if not file:
                raise ValueError(f"File not found: {file_id}")

            logger.info(f"Starting ingestion for file {file_id}")

            # Step 1: Download
            logger.info(f"Downloading PDF from S3: {file.s3_key}")
            pdf_bytes = self.s3_client.download_file(file.s3_key)

            # Step 2: Extract & Sanitize
            raw_text = extract_text_from_pdf(pdf_bytes)
            text = self._sanitize_text(raw_text)
            
            if not text.strip():
                raise ValueError("Extracted text is empty")
            
            logger.info(f"Extracted {len(text)} chars")

            # Step 3: Chunk
            chunks = chunk_text(text, chunk_size=512, overlap=102)
            if not chunks:
                raise ValueError("No chunks created")

            # Step 4: Embed
            logger.info(f"Generating embeddings for {len(chunks)} chunks...")
            embeddings = self.openai_client.get_embeddings(chunks)

            # Step 5: Upsert
            vector_ids = [f"{file_id}-chunk-{i}" for i in range(len(chunks))]
            metadata_list = [
                {
                    "file_id": file_id,
                    "chunk_index": i,
                    "chunk_text": self._sanitize_text(chunk[:200])  # Truncate and sanitize
                }
                for i, chunk in enumerate(chunks)
            ]

            logger.info(f"Upserting {len(embeddings)} vectors...")
            self.upstash_client.upsert_vectors(
                vectors=embeddings,
                ids=vector_ids,
                metadata=metadata_list,
            )

            # Step 6: Success
            await self.file_dao.update_status(session, file_id, IngestionStatus.COMPLETED)
            await session.commit()
            logger.info(f"✅ Ingestion complete: {file_id}")

        except Exception as e:
            logger.error(f"❌ Ingestion failed: {e}", exc_info=True)
            try:
                await self.file_dao.update_status(session, file_id, IngestionStatus.FAILED)
                await session.commit()
            except:
                pass
            raise
