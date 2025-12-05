"""
Contradiction Detection Service - Identifies conflicting statements in conversations

This service:
- Detects contradictions using semantic similarity and LLM analysis
- Classifies contradiction severity (high/medium/low)
- Stores contradictions in the database for tracking
"""
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.services.embedding_service import embedding_service
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


class Contradiction:
    """Data class for contradiction details"""

    def __init__(
        self,
        message_id1: str,
        message_id2: str,
        content1: str,
        content2: str,
        similarity_score: float,
        severity: str,
        explanation: str,
        detected_at: Optional[datetime] = None
    ):
        self.message_id1 = message_id1
        self.message_id2 = message_id2
        self.content1 = content1
        self.content2 = content2
        self.similarity_score = similarity_score
        self.severity = severity
        self.explanation = explanation
        self.detected_at = detected_at or datetime.now()

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "message_id1": self.message_id1,
            "message_id2": self.message_id2,
            "content1": self.content1,
            "content2": self.content2,
            "similarity_score": self.similarity_score,
            "severity": self.severity,
            "explanation": self.explanation,
            "detected_at": self.detected_at.isoformat()
        }


class ContradictionService:
    """Service for detecting contradictions in conversations"""

    def __init__(self):
        """Initialize contradiction detection service"""
        self.similarity_threshold = 0.85  # High semantic similarity
        self.opposition_threshold = 0.3   # Low similarity with opposite sentiment

    async def detect_contradictions(
        self,
        db: AsyncSession,
        conversation_id: str,
        new_message: Dict
    ) -> List[Contradiction]:
        """
        Detect contradictions between new message and conversation history

        Args:
            db: Database session
            conversation_id: Conversation identifier
            new_message: New message dict with 'id', 'content', 'agent_name'

        Returns:
            List of detected contradictions

        Raises:
            Exception: If detection fails
        """
        try:
            message_id = new_message["id"]
            content = new_message["content"]

            logger.debug(f"Detecting contradictions for message {message_id}")

            # Generate embedding for new message
            new_embedding = await embedding_service.generate_embedding(content)

            # Store embedding
            await embedding_service.store_embedding(
                db=db,
                message_id=message_id,
                embedding=new_embedding,
                metadata={
                    "conversation_id": conversation_id,
                    "agent_name": new_message.get("agent_name")
                }
            )

            # Find similar messages
            similar_messages = await embedding_service.find_similar_messages(
                db=db,
                conversation_id=conversation_id,
                query_embedding=new_embedding,
                threshold=self.similarity_threshold,
                limit=20
            )

            # Filter out the message itself
            similar_messages = [
                (msg_id, score) for msg_id, score in similar_messages
                if msg_id != message_id
            ]

            if not similar_messages:
                logger.debug("No similar messages found")
                return []

            # Retrieve message contents
            message_ids = [msg_id for msg_id, _ in similar_messages]
            query = text("""
                SELECT message_id, content, agent_name
                FROM messages
                WHERE message_id = ANY(:message_ids)
            """)
            result = await db.execute(query, {"message_ids": message_ids})
            message_data = {row[0]: {"content": row[1], "agent_name": row[2]} for row in result.fetchall()}

            # Check each similar message for contradictions
            contradictions = []
            for similar_msg_id, similarity_score in similar_messages:
                if similar_msg_id not in message_data:
                    continue

                similar_content = message_data[similar_msg_id]["content"]

                # Check if messages have opposing sentiment
                is_opposition = await self.check_sentiment_opposition(
                    content,
                    similar_content
                )

                if is_opposition:
                    # Get LLM analysis for explanation
                    explanation = await self._get_contradiction_explanation(
                        content,
                        similar_content
                    )

                    # Classify severity
                    severity = self.classify_severity(similarity_score, explanation)

                    contradiction = Contradiction(
                        message_id1=message_id,
                        message_id2=similar_msg_id,
                        content1=content,
                        content2=similar_content,
                        similarity_score=similarity_score,
                        severity=severity,
                        explanation=explanation
                    )

                    contradictions.append(contradiction)

                    # Store in database
                    await self._store_contradiction(db, conversation_id, contradiction)

            logger.info(f"Detected {len(contradictions)} contradictions for message {message_id}")
            return contradictions

        except Exception as e:
            logger.error(f"Error detecting contradictions: {str(e)}")
            raise

    async def check_sentiment_opposition(
        self,
        message1: str,
        message2: str
    ) -> bool:
        """
        Check if two messages have opposing sentiments using LLM

        Args:
            message1: First message content
            message2: Second message content

        Returns:
            True if messages express opposing viewpoints

        Raises:
            Exception: If LLM call fails
        """
        try:
            prompt = f"""Analyze these two statements and determine if they express opposing or contradictory viewpoints.

Statement 1: {message1}

Statement 2: {message2}

Consider:
1. Do they make opposite claims about the same topic?
2. Do they contradict each other's core assertions?
3. Would accepting both statements create a logical inconsistency?

Respond with ONLY "YES" if they are contradictory, or "NO" if they are not.
"""

            messages = [
                {"role": "system", "content": "You are an expert at detecting logical contradictions and opposing viewpoints."},
                {"role": "user", "content": prompt}
            ]

            response = await llm_service.get_completion(messages, model="gpt-4o-mini")
            response = response.strip().upper()

            is_opposition = response.startswith("YES")

            logger.debug(f"Sentiment opposition check: {is_opposition}")
            return is_opposition

        except Exception as e:
            logger.error(f"Error checking sentiment opposition: {str(e)}")
            # Default to False on error to avoid false positives
            return False

    def classify_severity(
        self,
        similarity_score: float,
        explanation: str
    ) -> str:
        """
        Classify contradiction severity

        Args:
            similarity_score: Semantic similarity (0-1)
            explanation: LLM explanation of the contradiction

        Returns:
            Severity level: "high", "medium", or "low"
        """
        # High severity: Very similar topic but contradictory (0.9+)
        if similarity_score >= 0.9:
            return "high"

        # Medium severity: Related topic with contradiction (0.85-0.9)
        elif similarity_score >= 0.85:
            # Check if explanation mentions strong contradiction indicators
            strong_indicators = [
                "directly contradicts",
                "completely opposite",
                "mutually exclusive",
                "impossible",
                "logically inconsistent"
            ]

            if any(indicator in explanation.lower() for indicator in strong_indicators):
                return "high"
            return "medium"

        # Low severity: Less similar but still contradictory
        else:
            return "low"

    async def _get_contradiction_explanation(
        self,
        message1: str,
        message2: str
    ) -> str:
        """
        Get LLM explanation of contradiction

        Args:
            message1: First message content
            message2: Second message content

        Returns:
            Explanation of the contradiction
        """
        try:
            prompt = f"""Explain how these two statements contradict each other. Be specific and concise (2-3 sentences).

Statement 1: {message1}

Statement 2: {message2}

Explanation:"""

            messages = [
                {"role": "system", "content": "You are an expert at analyzing logical contradictions."},
                {"role": "user", "content": prompt}
            ]

            explanation = await llm_service.get_completion(messages, model="gpt-4o-mini")
            return explanation.strip()

        except Exception as e:
            logger.error(f"Error getting contradiction explanation: {str(e)}")
            return "Unable to generate explanation"

    async def _store_contradiction(
        self,
        db: AsyncSession,
        conversation_id: str,
        contradiction: Contradiction
    ) -> None:
        """
        Store contradiction in database

        Args:
            db: Database session
            conversation_id: Conversation identifier
            contradiction: Contradiction object to store
        """
        try:
            query = text("""
                INSERT INTO contradictions (
                    conversation_id,
                    message_id1,
                    message_id2,
                    similarity_score,
                    severity,
                    explanation,
                    detected_at
                )
                VALUES (
                    :conversation_id,
                    :message_id1,
                    :message_id2,
                    :similarity_score,
                    :severity,
                    :explanation,
                    :detected_at
                )
            """)

            await db.execute(
                query,
                {
                    "conversation_id": conversation_id,
                    "message_id1": contradiction.message_id1,
                    "message_id2": contradiction.message_id2,
                    "similarity_score": contradiction.similarity_score,
                    "severity": contradiction.severity,
                    "explanation": contradiction.explanation,
                    "detected_at": contradiction.detected_at
                }
            )
            await db.commit()

            logger.debug(f"Stored contradiction between {contradiction.message_id1} and {contradiction.message_id2}")

        except Exception as e:
            logger.error(f"Error storing contradiction: {str(e)}")
            await db.rollback()
            raise


# Singleton instance
contradiction_service = ContradictionService()
