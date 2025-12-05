"""
Embedding Service - Generates and manages text embeddings for conversation quality analysis

This service:
- Generates embeddings using OpenAI's text-embedding-3-small model
- Caches embeddings in PostgreSQL with pgvector
- Provides similarity search for detecting contradictions and patterns
"""
import logging
from typing import List, Dict, Optional, Tuple
import numpy as np
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.config.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating and managing text embeddings"""

    def __init__(self):
        """Initialize embedding service with OpenAI client"""
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.default_model = "text-embedding-3-small"
        self.embedding_dimension = 1536  # text-embedding-3-small dimension

    async def generate_embedding(
        self,
        text: str,
        model: Optional[str] = None
    ) -> List[float]:
        """
        Generate embedding for a single text

        Args:
            text: Text to embed
            model: OpenAI embedding model (default: text-embedding-3-small)

        Returns:
            List of float values representing the embedding vector

        Raises:
            Exception: If OpenAI API call fails
        """
        model_to_use = model or self.default_model

        try:
            logger.debug(f"Generating embedding for text (length: {len(text)})")

            response = await self.client.embeddings.create(
                model=model_to_use,
                input=text,
                encoding_format="float"
            )

            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding with {len(embedding)} dimensions")

            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise

    async def batch_generate_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in a single API call

        Args:
            texts: List of texts to embed
            model: OpenAI embedding model (default: text-embedding-3-small)

        Returns:
            List of embedding vectors, one per input text

        Raises:
            Exception: If OpenAI API call fails
        """
        if not texts:
            return []

        model_to_use = model or self.default_model

        try:
            logger.debug(f"Generating {len(texts)} embeddings in batch")

            response = await self.client.embeddings.create(
                model=model_to_use,
                input=texts,
                encoding_format="float"
            )

            # Sort by index to maintain order
            embeddings = [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
            logger.debug(f"Generated {len(embeddings)} embeddings")

            return embeddings

        except Exception as e:
            logger.error(f"Error generating batch embeddings: {str(e)}")
            raise

    async def store_embedding(
        self,
        db: AsyncSession,
        message_id: str,
        embedding: List[float],
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Store embedding in PostgreSQL with pgvector

        Args:
            db: Database session
            message_id: Unique message identifier
            embedding: Embedding vector to store
            metadata: Optional metadata (conversation_id, agent_name, etc.)

        Raises:
            Exception: If database operation fails
        """
        try:
            # Convert embedding to pgvector format
            embedding_str = "[" + ",".join(map(str, embedding)) + "]"

            from sqlalchemy import bindparam
            import uuid
            query = text("""
                INSERT INTO message_embeddings (
                    id,
                    message_id,
                    embedding_vector,
                    embedding_model,
                    created_at
                )
                VALUES (
                    :id,
                    :message_id,
                    CAST(:embedding AS vector),
                    :model,
                    NOW()
                )
                ON CONFLICT (message_id)
                DO NOTHING
            """).bindparams(
                bindparam("id"),
                bindparam("message_id"),
                bindparam("embedding"),
                bindparam("model")
            )

            embedding_id = str(uuid.uuid4())
            model_name = metadata.get("model", "text-embedding-3-small") if metadata else "text-embedding-3-small"

            await db.execute(
                query,
                {
                    "id": embedding_id,
                    "message_id": message_id,
                    "embedding": embedding_str,
                    "model": model_name
                }
            )
            await db.commit()

            logger.debug(f"Stored embedding for message {message_id}")

        except Exception as e:
            logger.error(f"Error storing embedding: {str(e)}")
            await db.rollback()
            raise

    async def find_similar_messages(
        self,
        db: AsyncSession,
        conversation_id: str,
        query_embedding: List[float],
        threshold: float = 0.85,
        limit: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Find similar messages using cosine similarity

        Args:
            db: Database session
            conversation_id: Conversation to search within
            query_embedding: Query embedding vector
            threshold: Minimum similarity score (0-1, default: 0.85)
            limit: Maximum number of results

        Returns:
            List of (message_id, similarity_score) tuples, sorted by similarity desc

        Raises:
            Exception: If database query fails
        """
        try:
            # Convert embedding to pgvector format
            embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

            # Use cosine similarity operator (<=>)
            # pgvector returns distance (0 = identical, 2 = opposite)
            # We convert to similarity: similarity = 1 - (distance / 2)
            query = text("""
                SELECT
                    me.message_id,
                    1 - (me.embedding_vector <=> CAST(:query_embedding AS vector)) / 2 AS similarity
                FROM message_embeddings me
                JOIN messages m ON me.message_id = m.id
                WHERE m.conversation_id = :conversation_id
                    AND 1 - (me.embedding_vector <=> CAST(:query_embedding AS vector)) / 2 >= :threshold
                ORDER BY me.embedding_vector <=> CAST(:query_embedding AS vector)
                LIMIT :limit
            """)

            result = await db.execute(
                query,
                {
                    "query_embedding": embedding_str,
                    "conversation_id": conversation_id,
                    "threshold": threshold,
                    "limit": limit
                }
            )

            similar_messages = [(row[0], float(row[1])) for row in result.fetchall()]

            logger.debug(
                f"Found {len(similar_messages)} similar messages "
                f"(threshold: {threshold}, conversation: {conversation_id})"
            )

            return similar_messages

        except Exception as e:
            logger.error(f"Error finding similar messages: {str(e)}")
            raise

    def calculate_cosine_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score (0-1, where 1 is identical)
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)

        # Ensure result is in [0, 1] range (handle floating point errors)
        return float(max(0.0, min(1.0, similarity)))


# Singleton instance
embedding_service = EmbeddingService()
