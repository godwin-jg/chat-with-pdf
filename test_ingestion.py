"""
Test script to manually trigger ingestion and check configuration.
"""
import asyncio
import sys
from database import get_async_session_local
from services.file_service.ingestion_service import IngestionService
from dao.file_dao import FileDAO
from dao.models.file import IngestionStatus
from config import settings

async def test_ingestion():
    """Test the ingestion pipeline."""
    print("=== Configuration Check ===")
    print(f"UPSTASH_VECTOR_REST_URL: {'SET' if settings.UPSTASH_VECTOR_REST_URL else 'NOT SET'}")
    print(f"UPSTASH_VECTOR_REST_TOKEN: {'SET' if settings.UPSTASH_VECTOR_REST_TOKEN else 'NOT SET'}")
    print(f"UPSTASH_VECTOR_NAMESPACE: {settings.UPSTASH_VECTOR_NAMESPACE}")
    print(f"OPENAI_API_KEY: {'SET' if settings.OPENAI_API_KEY else 'NOT SET'}")
    print()
    
    if not settings.UPSTASH_VECTOR_REST_URL or not settings.UPSTASH_VECTOR_REST_TOKEN:
        print("❌ Upstash Vector credentials not configured!")
        print("   Set UPSTASH_VECTOR_REST_URL and UPSTASH_VECTOR_REST_TOKEN in .env")
        return
    
    file_id = "500107f2-4445-4be2-9a5e-aca7144780d2"
    
    print(f"=== Testing Ingestion for file_id: {file_id} ===")
    
    # Reset file status to "uploaded" if it's "failed"
    AsyncSessionLocal = get_async_session_local()
    async with AsyncSessionLocal() as session:
        file_dao = FileDAO()
        file = await file_dao.get_by_id(session, file_id)
        
        if file:
            print(f"File found: {file.s3_key}")
            print(f"Current status: {file.ingestion_status}")
            
            if file.ingestion_status == IngestionStatus.FAILED:
                print("Resetting status to 'uploaded' for re-ingestion...")
                await file_dao.update_status(session, file_id, IngestionStatus.UPLOADED)
                await session.commit()
                print("Status reset to 'uploaded'")
        
        # Now trigger ingestion
        print("\n=== Starting Ingestion Pipeline ===")
        ingestion_service = IngestionService()
        
        try:
            await ingestion_service.process_file_ingestion(session, file_id)
            print("✅ Ingestion completed successfully!")
        except Exception as e:
            print(f"❌ Ingestion failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ingestion())

