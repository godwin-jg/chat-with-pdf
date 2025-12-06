"""
File model for storing PDF file metadata.
"""
from sqlalchemy import Column, String, Enum
from sqlalchemy.dialects.postgresql import UUID
import enum
from dao.models.base import BaseModel


class IngestionStatus(str, enum.Enum):
    """Enumeration for file ingestion status."""

    UPLOADED = "uploaded"
    COMPLETED = "completed"
    FAILED = "failed"


class File(BaseModel):
    """Model representing a PDF file."""

    __tablename__ = "files"

    s3_key = Column(String, nullable=False, unique=True, index=True)
    ingestion_status = Column(
        Enum(IngestionStatus),
        nullable=False,
        default=IngestionStatus.UPLOADED,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<File(id={self.id}, s3_key={self.s3_key}, status={self.ingestion_status})>"

