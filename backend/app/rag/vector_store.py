import math
from typing import List, Dict, Any, Optional
from uuid import UUID
import httpx
from app.core.config import settings

class VectorPoint:
    def __init__(
        self,
        id: str,
        vector: List[float],
        payload: Dict[str, Any]
    ):
        self.id = id
        self.vector = vector
        self.payload = payload

class ScoredPoint:
    def __init__(
        self,
        id: str,
        score: float,
        payload: Dict[str, Any]
    ):
        self.id = id
        self.score = score
        self.payload = payload

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "score": self.score,
            "payload": self.payload
        }

class QdrantVectorStore:
    """Qdrant vector store with REST client and automatic in-memory fallback."""

    def __init__(
        self,
        qdrant_url: Optional[str] = None,
        default_collection: str = "ragguard_chunks"
    ):
        self.qdrant_url = (qdrant_url or getattr(settings, "QDRANT_URL", "http://localhost:6333")).rstrip("/")
        self.default_collection = default_collection
        # In-memory point registry: collection_name -> List[VectorPoint]
        self._memory_store: Dict[str, List[VectorPoint]] = {}

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(a * b for a, b in zip(v1, v2))
        norm_a = math.sqrt(sum(a * a for a in v1))
        norm_b = math.sqrt(sum(b * b for b in v2))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    async def ensure_collection(self, collection_name: Optional[str] = None, vector_size: int = 1536) -> bool:
        coll = collection_name or self.default_collection
        if coll not in self._memory_store:
            self._memory_store[coll] = []

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.qdrant_url}/collections/{coll}")
                if res.status_code == 200:
                    return True
                
                # Create collection if it doesn't exist
                create_payload = {
                    "vectors": {
                        "size": vector_size,
                        "distance": "Cosine"
                    }
                }
                put_res = await client.put(f"{self.qdrant_url}/collections/{coll}", json=create_payload)
                return put_res.status_code in (200, 201)
        except Exception:
            # Running offline / fallback
            return True

    async def upsert_points(
        self,
        points: List[VectorPoint],
        collection_name: Optional[str] = None,
        vector_size: int = 1536
    ) -> bool:
        coll = collection_name or self.default_collection
        if coll not in self._memory_store:
            self._memory_store[coll] = []

        # Update in-memory registry
        point_ids = {p.id for p in points}
        self._memory_store[coll] = [p for p in self._memory_store[coll] if p.id not in point_ids] + points

        try:
            await self.ensure_collection(coll, vector_size=vector_size)
            qdrant_payload = {
                "points": [
                    {
                        "id": p.id,
                        "vector": p.vector,
                        "payload": p.payload
                    }
                    for p in points
                ]
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.put(f"{self.qdrant_url}/collections/{coll}/points", json=qdrant_payload)
                return res.status_code in (200, 201)
        except Exception:
            return True

    async def search(
        self,
        query_vector: List[float],
        project_id: UUID,
        top_k: int = 5,
        similarity_threshold: float = 0.0,
        collection_name: Optional[str] = None
    ) -> List[ScoredPoint]:
        coll = collection_name or self.default_collection
        str_project_id = str(project_id)

        # Attempt query against live Qdrant instance
        try:
            search_body = {
                "vector": query_vector,
                "limit": top_k,
                "score_threshold": similarity_threshold if similarity_threshold > 0 else None,
                "filter": {
                    "must": [
                        {
                            "key": "project_id",
                            "match": {"value": str_project_id}
                        }
                    ]
                },
                "with_payload": True
            }
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(f"{self.qdrant_url}/collections/{coll}/points/search", json=search_body)
                if res.status_code == 200:
                    data = res.json()
                    scored_points = []
                    for item in data.get("result", []):
                        scored_points.append(
                            ScoredPoint(
                                id=str(item["id"]),
                                score=float(item.get("score", 0.0)),
                                payload=item.get("payload", {})
                            )
                        )
                    return scored_points
        except Exception:
            pass

        # Fallback to local in-memory vector index with project isolation
        points = self._memory_store.get(coll, [])
        matched: List[ScoredPoint] = []

        for p in points:
            if str(p.payload.get("project_id")) == str_project_id:
                score = self._cosine_similarity(query_vector, p.vector)
                if score >= similarity_threshold:
                    matched.append(ScoredPoint(id=p.id, score=score, payload=p.payload))

        matched.sort(key=lambda x: x.score, reverse=True)
        return matched[:top_k]

    async def delete_by_document(self, document_id: UUID, collection_name: Optional[str] = None) -> bool:
        coll = collection_name or self.default_collection
        str_doc_id = str(document_id)

        if coll in self._memory_store:
            self._memory_store[coll] = [
                p for p in self._memory_store[coll] if str(p.payload.get("document_id")) != str_doc_id
            ]

        try:
            delete_body = {
                "filter": {
                    "must": [
                        {
                            "key": "document_id",
                            "match": {"value": str_doc_id}
                        }
                    ]
                }
            }
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(f"{self.qdrant_url}/collections/{coll}/points/delete", json=delete_body)
                return res.status_code == 200
        except Exception:
            return True

# Singleton vector store instance
vector_store = QdrantVectorStore()
