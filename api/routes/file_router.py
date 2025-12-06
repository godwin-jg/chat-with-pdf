"""
File router for file management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from services.file_service.upload_service import UploadService
from services.file_service.file_service import FileService
from api.schemas.request import PresignRequest
from api.schemas.response import (
    PresignResponse,
    FileResponse,
    FileListResponse,
    FileListItem,
)
from typing import Optional

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/presign", response_model=PresignResponse, status_code=200)
async def generate_presigned_url(
    request: PresignRequest,
) -> PresignResponse:
    """
    Generate a presigned URL for uploading a PDF file to S3.

    This endpoint generates a unique file_id and returns a presigned POST URL
    that allows the client to upload a file directly to S3. The file record
    is NOT created in the database at this point - it will be created by the
    webhook when the file is actually uploaded to S3.

    Args:
        request: PresignRequest containing the filename

    Returns:
        PresignResponse with file_id, presigned_url, and expiration info
    """
    upload_service = UploadService()
    result = upload_service.generate_presigned_upload(request.filename)

    return PresignResponse(
        file_id=result["file_id"],
        presigned_url=result["presigned_url"],
        expires_in_seconds=result["expires_in_seconds"],
    )


@router.get("", response_model=FileListResponse, status_code=200)
async def list_files(
    limit: int = Query(20, ge=1, le=100, description="Number of files to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    session: AsyncSession = Depends(get_db),
) -> FileListResponse:
    """
    List all files with pagination.

    Args:
        limit: Maximum number of files to return (1-100)
        offset: Number of files to skip
        session: Database session

    Returns:
        FileListResponse with paginated list of files
    """
    file_service = FileService()
    files, total = await file_service.list_files(
        session=session, limit=limit, offset=offset
    )

    file_items = [
        FileListItem(
            file_id=str(file.id),
            s3_key=file.s3_key,
            ingestion_status=file.ingestion_status.value,
            created_at=file.created_at.isoformat(),
            updated_at=file.updated_at.isoformat(),
        )
        for file in files
    ]

    return FileListResponse(
        files=file_items, total=total, limit=limit, offset=offset
    )


@router.get("/{file_id}", response_model=FileResponse, status_code=200)
async def get_file(
    file_id: str,
    session: AsyncSession = Depends(get_db),
) -> FileResponse:
    """
    Get file details with presigned download URL.

    Args:
        file_id: File identifier (UUID)
        session: Database session

    Returns:
        FileResponse with file details and download URL

    Raises:
        HTTPException: 404 if file not found
    """
    file_service = FileService()
    file_data = await file_service.get_file_with_download_url(
        session=session, file_id=file_id
    )

    if not file_data:
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(**file_data)

