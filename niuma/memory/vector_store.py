"""Vector storage for semantic memory using ChromaDB."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from niuma.config import get_settings
from niuma.llm.client import LLMClient


@dataclass
class VectorDocument:
    """A document stored in vector storage."""

    id: str
    content: str
    metadata: dict[str, Any]
    embedding: list[float] | None = None


class VectorStore:
    """Vector storage using ChromaDB for semantic search."""

    def __init__(
        self,
        collection_name: str = "niuma_memory",
        persist_directory: Path | None = None,
        embedding_model: str | None = None,
    ) -> None:
        """Initialize vector store.

        Args:
            collection_name: Name of the collection.
            persist_directory: Directory to persist data.
            embedding_model: Embedding model name.
        """
        settings = get_settings()
        self.collection_name = collection_name
        self.persist_directory = persist_directory or settings.memory.vector_store_path
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.embedding_model = embedding_model or settings.memory.embedding_model

        self._client: Any | None = None
        self._collection: Any | None = None
        self._llm: LLMClient | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the vector store."""
        if self._initialized:
            return

        try:
            import chromadb

            self._client = chromadb.Client(
                chromadb.Settings(
                    persist_directory=str(self.persist_directory),
                    is_persistent=True,
                )
            )

            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )

            self._llm = LLMClient()

            self._initialized = True

        except ImportError:
            raise RuntimeError(
                "ChromaDB not installed. Install with: pip install chromadb"
            )

    async def add(
        self,
        documents: list[str],
        ids: list[str] | None = None,
        metadatas: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        """Add documents to vector store.

        Args:
            documents: List of text documents.
            ids: Optional document IDs (auto-generated if not provided).
            metadatas: Optional metadata for each document.

        Returns:
            List of document IDs.
        """
        if not self._initialized:
            await self.initialize()

        if ids is None:
            import uuid

            ids = [str(uuid.uuid4()) for _ in documents]

        if metadatas is None:
            metadatas = [{} for _ in documents]

        # Generate embeddings
        embeddings = await self._llm.embed(documents)

        # Add to collection
        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        return ids

    async def search(
        self,
        query: str,
        n_results: int = 5,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar documents.

        Args:
            query: Search query.
            n_results: Number of results to return.
            filter_dict: Optional filter for metadata.

        Returns:
            List of results with content, metadata, and distance.
        """
        if not self._initialized:
            await self.initialize()

        # Generate query embedding
        query_embedding = await self._llm.embed([query])

        # Search
        results = self._collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            where=filter_dict,
        )

        # Format results
        formatted = []
        for i in range(len(results["documents"][0])):
            formatted.append({
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            })

        return formatted

    async def delete(self, ids: list[str]) -> bool:
        """Delete documents by ID.

        Args:
            ids: List of document IDs to delete.

        Returns:
            True if successful.
        """
        if not self._initialized:
            await self.initialize()

        self._collection.delete(ids=ids)
        return True

    async def update(
        self,
        ids: list[str],
        documents: list[str] | None = None,
        metadatas: list[dict[str, Any]] | None = None,
    ) -> bool:
        """Update documents.

        Args:
            ids: Document IDs to update.
            documents: New document content (optional).
            metadatas: New metadata (optional).

        Returns:
            True if successful.
        """
        if not self._initialized:
            await self.initialize()

        # Generate new embeddings if documents provided
        embeddings = None
        if documents:
            embeddings = await self._llm.embed(documents)

        self._collection.update(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        return True

    async def get(self, ids: list[str]) -> list[dict[str, Any]]:
        """Get documents by ID.

        Args:
            ids: Document IDs to retrieve.

        Returns:
            List of documents.
        """
        if not self._initialized:
            await self.initialize()

        results = self._collection.get(ids=ids)

        return [
            {
                "id": results["ids"][i],
                "content": results["documents"][i],
                "metadata": results["metadatas"][i],
            }
            for i in range(len(results["ids"]))
        ]

    async def clear(self) -> None:
        """Clear all documents from the collection."""
        if not self._initialized:
            await self.initialize()

        ids = self._collection.get()["ids"]
        if ids:
            self._collection.delete(ids=ids)

    async def count(self) -> int:
        """Get the number of documents in the collection."""
        if not self._initialized:
            await self.initialize()

        return self._collection.count()

    async def get_stats(self) -> dict[str, Any]:
        """Get vector store statistics."""
        if not self._initialized:
            await self.initialize()

        return {
            "collection_name": self.collection_name,
            "document_count": self._collection.count(),
            "persist_directory": str(self.persist_directory),
            "embedding_model": self.embedding_model,
        }


class SemanticMemory:
    """High-level semantic memory interface."""

    def __init__(
        self,
        vector_store: VectorStore | None = None,
    ) -> None:
        """Initialize semantic memory.

        Args:
            vector_store: Optional vector store instance.
        """
        self.vector_store = vector_store or VectorStore()

    async def remember(
        self,
        content: str,
        category: str = "general",
        tags: list[str] | None = None,
    ) -> str:
        """Store a memory with semantic indexing.

        Args:
            content: Memory content.
            category: Memory category.
            tags: Optional tags.

        Returns:
            Memory ID.
        """
        import uuid

        memory_id = str(uuid.uuid4())
        metadata = {
            "category": category,
            "tags": tags or [],
            "created_at": str(uuid.uuid1()),
        }

        await self.vector_store.add(
            documents=[content],
            ids=[memory_id],
            metadatas=[metadata],
        )

        return memory_id

    async def recall(
        self,
        query: str,
        category: str | None = None,
        n_results: int = 5,
    ) -> list[dict[str, Any]]:
        """Recall memories similar to query.

        Args:
            query: Search query.
            category: Filter by category.
            n_results: Number of results.

        Returns:
            List of relevant memories.
        """
        filter_dict = None
        if category:
            filter_dict = {"category": category}

        return await self.vector_store.search(
            query=query,
            n_results=n_results,
            filter_dict=filter_dict,
        )

    async def forget(self, memory_id: str) -> bool:
        """Remove a memory.

        Args:
            memory_id: ID of memory to remove.

        Returns:
            True if removed.
        """
        return await self.vector_store.delete([memory_id])
