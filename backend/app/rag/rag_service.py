import time
from typing import List, Optional
from uuid import UUID
from app.rag.embeddings import EmbeddingProvider, get_embedding_provider
from app.rag.llm import LLMProvider, get_llm_provider
from app.rag.vector_store import QdrantVectorStore, vector_store
from app.schemas.rag import SourceCitation, QueryResponse

class RAGService:
    """Core RAG retrieval and answer generation service."""

    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        llm_provider: Optional[LLMProvider] = None,
        store: Optional[QdrantVectorStore] = None
    ):
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.llm_provider = llm_provider or get_llm_provider()
        self.vector_store = store or vector_store

    async def retrieve(
        self,
        project_id: UUID,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.0
    ) -> List[SourceCitation]:
        """Generate query vector and search vector store for matching project chunks."""
        query_vector = await self.embedding_provider.embed_query(query)
        scored_points = await self.vector_store.search(
            query_vector=query_vector,
            project_id=project_id,
            top_k=top_k,
            similarity_threshold=similarity_threshold
        )

        citations: List[SourceCitation] = []
        for sp in scored_points:
            p = sp.payload
            citations.append(
                SourceCitation(
                    document=p.get("filename", "unknown"),
                    document_id=UUID(p["document_id"]) if isinstance(p.get("document_id"), str) else p.get("document_id"),
                    chunk_id=UUID(sp.id) if isinstance(sp.id, str) else sp.id,
                    page=p.get("page_number"),
                    chunk_index=p.get("chunk_index", 0),
                    text=p.get("text", ""),
                    score=round(sp.score, 4)
                )
            )
        return citations

    async def generate(
        self,
        question: str,
        retrieved_chunks: List[SourceCitation],
        system_prompt: Optional[str] = None
    ) -> str:
        """Construct grounded prompt and generate answer via LLM provider."""
        system_prompt = system_prompt or (
            "You are a helpful and precise organizational AI assistant. "
            "Answer the user's question accurately using ONLY the provided context snippets below. "
            "If the context does not contain enough information to answer the question, state that clearly."
        )

        if not retrieved_chunks:
            context_text = "No relevant context found in the project's documentation."
        else:
            context_blocks = []
            for c in retrieved_chunks:
                page_info = f", Page: {c.page}" if c.page else ""
                context_blocks.append(f"[Source: {c.document}{page_info}]\n{c.text}")
            context_text = "\n\n---\n\n".join(context_blocks)

        prompt = f"Context:\n{context_text}\n\nQuestion: {question}\n\nAnswer:"
        return await self.llm_provider.generate_answer(prompt=prompt, system_prompt=system_prompt)

    async def answer(
        self,
        project_id: UUID,
        question: str,
        top_k: int = 5,
        similarity_threshold: float = 0.0
    ) -> QueryResponse:
        """Complete RAG pipeline: Retrieve relevant context -> Generate grounded answer -> Return citations."""
        start_time = time.time()
        
        # 1. Retrieval
        citations = await self.retrieve(
            project_id=project_id,
            query=question,
            top_k=top_k,
            similarity_threshold=similarity_threshold
        )

        # 2. Generation
        answer_text = await self.generate(
            question=question,
            retrieved_chunks=citations
        )

        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        return QueryResponse(
            question=question,
            answer=answer_text,
            sources=citations,
            model=self.llm_provider.model_name,
            latency_ms=elapsed_ms
        )

# Factory helper
def get_rag_service() -> RAGService:
    return RAGService()
