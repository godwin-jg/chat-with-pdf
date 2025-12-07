"""
Webhook router for S3 event handling.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from services.file_service.ingestion_service import IngestionService
from api.schemas.request import WebhookIngestRequest
from api.schemas.response import WebhookIngestResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/ingest", response_model=WebhookIngestResponse, status_code=200)
async def ingest_file(
    request: WebhookIngestRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
) -> WebhookIngestResponse:
    """
    Webhook endpoint for S3 upload events.

    This endpoint is called by AWS Lambda when a file is uploaded to S3.
    It:
    1. Extracts the file_id from the S3 key
    2. Creates a file record in the database with status "uploaded"
    3. Starts background task to process ingestion (extract, chunk, embed, upsert)

    Args:
        request: WebhookIngestRequest containing S3 bucket and key
        background_tasks: FastAPI BackgroundTasks for async processing
        session: Database session

    Returns:
        WebhookIngestResponse with file details

    Raises:
        HTTPException: 400 if file_id extraction fails or file already exists
    """
    ingestion_service = IngestionService()

    file = await ingestion_service.create_file_from_s3_event(
        session=session, s3_bucket=request.s3_bucket, s3_key=request.s3_key
    )

    if not file:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid S3 key format. Expected: uploads/{{file_id}}.pdf",
        )

    await session.commit()

    file_id_str = str(file.id)
    background_tasks.add_task(
        _process_ingestion_background,
        file_id=file_id_str,
    )

    logger.info(
        f"File record created and background ingestion started for file_id: {file_id_str}"
    )

    from dao.models.file import IngestionStatus
    
    status_value = file.ingestion_status.value if isinstance(file.ingestion_status, IngestionStatus) else str(file.ingestion_status)
    
    return WebhookIngestResponse(
        file_id=file_id_str,
        s3_key=file.s3_key,
        ingestion_status=status_value,
        message="File record created successfully. Ingestion started in background.",
    )


async def _process_ingestion_background(file_id: str) -> None:
    """
    Background task to process file ingestion.

    This function runs asynchronously after the webhook response is sent.
    It performs the full ingestion pipeline: Download -> Extract -> Chunk -> Embed -> Upsert.

    Args:
        file_id: File ID (UUID string)
    """
    from database import get_async_session_local
    from services.file_service.ingestion_service import IngestionService

    ingestion_service = IngestionService()

    AsyncSessionLocal = get_async_session_local()
    async with AsyncSessionLocal() as session:
        try:
            await ingestion_service.process_file_ingestion(session, file_id)
        except Exception as e:
            logger.error(
                f"Background ingestion task failed for file_id {file_id}: {e}",
                exc_info=True,
            )
        finally:
            await session.close()

