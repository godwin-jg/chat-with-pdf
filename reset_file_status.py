"""
Script to reset file status back to 'uploaded' for re-ingestion.
"""
import asyncio
from database import get_async_session_local
from dao.file_dao import FileDAO
from dao.models.file import IngestionStatus

async def reset_file_status(file_id: str):
    """Reset file status to 'uploaded'."""
    AsyncSessionLocal = get_async_session_local()
    async with AsyncSessionLocal() as session:
        file_dao = FileDAO()
        
        # Get current file
        file = await file_dao.get_by_id(session, file_id)
        if not file:
            print(f"❌ File not found: {file_id}")
            return
        
        print(f"File found: {file.s3_key}")
        print(f"Current status: {file.ingestion_status}")
        
        # Reset to uploaded
        await file_dao.update_status(session, file_id, IngestionStatus.UPLOADED)
        await session.commit()
        
        # Verify
        file = await file_dao.get_by_id(session, file_id)
        print(f"✅ Status updated to: {file.ingestion_status}")

if __name__ == "__main__":
    file_id = "500107f2-4445-4be2-9a5e-aca7144780d2"
    asyncio.run(reset_file_status(file_id))

