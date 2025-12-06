"""
Upstash Vector client for storing and querying embeddings.
"""
import logging
import json
from typing import List, Dict, Any, Optional
import requests
from config import settings

logger = logging.getLogger(__name__)


class UpstashVectorClient:
    """Client for Upstash Vector operations."""

    def __init__(self):
        self.base_url = (settings.UPSTASH_VECTOR_REST_URL or "").rstrip("/")
        self.token = settings.UPSTASH_VECTOR_REST_TOKEN or ""
        self.namespace = settings.UPSTASH_VECTOR_NAMESPACE

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def upsert_vectors(
        self,
        vectors: List[List[float]],
        ids: List[str],
        metadata: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Upsert vectors in batches.
        """
        if not self.base_url or not self.token:
            raise ValueError("Upstash Vector credentials not configured.")

        if not (len(vectors) == len(ids) == len(metadata)):
            raise ValueError("Vectors, IDs, and metadata must have same length.")

        # Prepare data points (metadata already sanitized in ingestion_service)
        data = []
        for vector, vector_id, meta in zip(vectors, ids, metadata):
            data.append({
                "id": str(vector_id),
                "vector": vector,
                "metadata": meta,
            })

        url = f"{self.base_url}/upsert"
        params = {}
        if self.namespace:
            params["namespace"] = self.namespace

        # Batch to avoid payload limits (20 vectors ≈ 500KB)
        BATCH_SIZE = 20
        total_upserted = 0

        for i in range(0, len(data), BATCH_SIZE):
            batch = data[i:i + BATCH_SIZE]
            
            try:
                response = requests.post(
                    url,
                    json=batch,  # Send array directly, not wrapped
                    headers=self._get_headers(),
                    params=params,
                    timeout=30,
                )
                response.raise_for_status()
                total_upserted += len(batch)
                logger.info(f"Upserted batch {i//BATCH_SIZE + 1} ({len(batch)} vectors)")
                
            except requests.exceptions.RequestException as e:
                error_body = e.response.text if e.response else str(e)
                logger.error(f"Upstash upsert failed: {error_body}")
                raise Exception(f"Upstash Upsert Failed: {error_body}")

        return {"upserted": total_upserted}

    def query_vectors(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query vectors from Upstash Vector."""
        url = f"{self.base_url}/query"
        params = {}
        if self.namespace:
            params["namespace"] = self.namespace

        payload = {
            "vector": query_vector,
            "topK": top_k,
            "includeMetadata": True
        }
        if filter:
            payload["filter"] = filter

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            return response.json().get("result", [])
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise


_upstash_client = None

def get_upstash_client() -> UpstashVectorClient:
    global _upstash_client
    if _upstash_client is None:
        _upstash_client = UpstashVectorClient()
    return _upstash_client
