"""
Retrieve router for vector search testing.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from api.schemas.request import RetrieveRequest
from api.schemas.response import RetrieveResponse, RetrieveResultItem
from core.openai.openai_client import get_openai_client
from core.vector.upstash_client import get_upstash_client
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/retrieve", tags=["retrieve"])


@router.post("", response_model=RetrieveResponse, status_code=200)
async def retrieve_chunks(
    request: RetrieveRequest,
    session: AsyncSession = Depends(get_db),
) -> RetrieveResponse:
    """
    Retrieve relevant chunks from vector database using semantic search.

    This endpoint is for testing/debugging retrieval independently.
    It performs a semantic search across specified file_ids and returns
    the most relevant chunks with similarity scores.

    Args:
        request: RetrieveRequest containing file_ids, query, and top_k
        session: Database session (for validation, not used for retrieval)

    Returns:
        RetrieveResponse with list of retrieved chunks

    Raises:
        HTTPException: 400 if file_ids are invalid or query is empty
    """
    openai_client = get_openai_client()
    upstash_client = get_upstash_client()

    try:
        # Step 1: Generate embedding for the query
        logger.info(f"Generating query embedding for: {request.query[:50]}...")
        query_embeddings = openai_client.get_embeddings([request.query])
        if not query_embeddings or len(query_embeddings) == 0:
            raise HTTPException(
                status_code=500, detail="Failed to generate query embedding"
            )
        query_vector = query_embeddings[0]

        # Step 2: Build metadata filter for file_ids
        # Upstash supports filtering with: "file_id = 'uuid1' OR file_id = 'uuid2'"
        if len(request.file_ids) == 1:
            filter_str = f"file_id = '{request.file_ids[0]}'"
        else:
            # Multiple file_ids: use OR conditions
            filter_parts = [f"file_id = '{fid}'" for fid in request.file_ids]
            filter_str = " OR ".join(filter_parts)

        logger.info(
            f"Querying Upstash Vector with filter: {filter_str}, top_k={request.top_k}"
        )

        # Step 3: Query Upstash Vector
        results = upstash_client.query_vectors(
            query_vector=query_vector,
            top_k=request.top_k,
            filter=filter_str,
        )

        # Step 4: Format results
        retrieve_items = []
        for result in results:
            metadata = result.get("metadata", {})
            retrieve_items.append(
                RetrieveResultItem(
                    chunk_id=result.get("id", ""),
                    file_id=metadata.get("file_id", ""),
                    chunk_text=metadata.get("chunk_text", ""),
                    similarity_score=result.get("score", 0.0),
                )
            )

        logger.info(f"Retrieved {len(retrieve_items)} chunks")

        return RetrieveResponse(results=retrieve_items)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving chunks: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve chunks: {str(e)}"
        )

