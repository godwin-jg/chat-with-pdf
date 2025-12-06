"""
Webhook router for S3 event handling.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from services.file_service.ingestion_service import IngestionService
from api.schemas.request import WebhookIngestRequest
from api.schemas.response import WebhookIngestResponse

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/ingest", response_model=WebhookIngestResponse, status_code=200)
async def ingest_file(
    request: WebhookIngestRequest,
    session: AsyncSession = Depends(get_db),
) -> WebhookIngestResponse:
    """
    Webhook endpoint for S3 upload events.

    This endpoint is called by AWS Lambda when a file is uploaded to S3.
    It extracts the file_id from the S3 key and creates a file record
    in the database with status "uploaded".

    Args:
        request: WebhookIngestRequest containing S3 bucket and key
        session: Database session

    Returns:
        WebhookIngestResponse with file details

    Raises:
        HTTPException: 400 if file_id extraction fails or file already exists
    """
    ingestion_service = IngestionService()

    # Create file record from S3 event
    file = await ingestion_service.create_file_from_s3_event(
        session=session, s3_bucket=request.s3_bucket, s3_key=request.s3_key
    )

    if not file:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid S3 key format. Expected: uploads/{{file_id}}.pdf",
        )

    # Commit the transaction
    await session.commit()

    from dao.models.file import IngestionStatus
    
    # Get ingestion_status as string
    status_value = file.ingestion_status.value if isinstance(file.ingestion_status, IngestionStatus) else str(file.ingestion_status)
    
    return WebhookIngestResponse(
        file_id=str(file.id),
        s3_key=file.s3_key,
        ingestion_status=status_value,
        message="File record created successfully",
    )

