"""
Health Scoring Service - Calculates real-time conversation quality metrics

This service:
- Calculates composite health scores (0-100)
- Tracks coherence, progress, and productivity metrics
- Provides status assessment (excellent/good/fair/poor)
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)


class HealthScore:
    """Data class for conversation health score"""

    def __init__(
        self,
        conversation_id: str,
        overall_score: float,
        coherence_score: float,
        progress_score: float,
        productivity_score: float,
        status: str,
        details: Dict,
        calculated_at: Optional[datetime] = None
    ):
        self.conversation_id = conversation_id
        self.overall_score = overall_score
        self.coherence_score = coherence_score
        self.progress_score = progress_score
        self.productivity_score = productivity_score
        self.status = status
        self.details = details
        self.calculated_at = calculated_at or datetime.now()

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "conversation_id": self.conversation_id,
            "overall_score": round(self.overall_score, 2),
            "coherence_score": round(self.coherence_score, 2),
            "progress_score": round(self.progress_score, 2),
            "productivity_score": round(self.productivity_score, 2),
            "status": self.status,
            "details": self.details,
            "calculated_at": self.calculated_at.isoformat()
        }


class HealthScoringService:
    """Service for calculating conversation health scores"""

    def __init__(self):
        """Initialize health scoring service"""
        # Weights for composite score
        self.coherence_weight = 0.4    # 40% - Most important
        self.progress_weight = 0.3     # 30% - Second priority
        self.productivity_weight = 0.3  # 30% - Efficiency matters

        # Status thresholds
        self.excellent_threshold = 85
        self.good_threshold = 70
        self.fair_threshold = 50

    async def calculate_health_score(
        self,
        db: AsyncSession,
        conversation_id: str,
        recent_messages: List[Dict]
    ) -> HealthScore:
        """
        Calculate comprehensive health score for conversation

        Args:
            db: Database session
            conversation_id: Conversation identifier
            recent_messages: List of recent message dicts with 'id', 'content', 'agent_name', 'timestamp'

        Returns:
            HealthScore object with all metrics

        Raises:
            Exception: If calculation fails
        """
        try:
            if not recent_messages:
                logger.warning(f"No messages provided for conversation {conversation_id}")
                return self._create_default_score(conversation_id)

            logger.debug(f"Calculating health score for {len(recent_messages)} messages")

            # Calculate individual metrics
            coherence_score = await self.calculate_coherence(db, recent_messages)
            progress_score = await self.calculate_progress(recent_messages)
            productivity_score = await self.calculate_productivity(recent_messages)

            # Calculate weighted overall score
            overall_score = (
                coherence_score * self.coherence_weight +
                progress_score * self.progress_weight +
                productivity_score * self.productivity_weight
            )

            # Determine status
            status = self._determine_status(overall_score)

            # Compile details
            details = {
                "message_count": len(recent_messages),
                "unique_agents": len(set(msg["agent_name"] for msg in recent_messages)),
                "weights": {
                    "coherence": self.coherence_weight,
                    "progress": self.progress_weight,
                    "productivity": self.productivity_weight
                }
            }

            health_score = HealthScore(
                conversation_id=conversation_id,
                overall_score=overall_score,
                coherence_score=coherence_score,
                progress_score=progress_score,
                productivity_score=productivity_score,
                status=status,
                details=details
            )

            # Store in database
            await self._store_health_score(db, health_score)

            logger.info(
                f"Calculated health score for {conversation_id}: "
                f"{overall_score:.1f} ({status})"
            )

            return health_score

        except Exception as e:
            logger.error(f"Error calculating health score: {str(e)}")
            raise

    async def calculate_coherence(
        self,
        db: AsyncSession,
        messages: List[Dict]
    ) -> float:
        """
        Calculate coherence score based on semantic similarity between messages

        Args:
            db: Database session
            messages: List of message dicts

        Returns:
            Coherence score (0-100)
        """
        try:
            if len(messages) < 2:
                return 100.0  # Single message is perfectly coherent

            # Generate embeddings for all messages
            contents = [msg["content"] for msg in messages]
            embeddings = await embedding_service.batch_generate_embeddings(contents)

            # Calculate pairwise similarities for consecutive messages
            similarities = []
            for i in range(len(embeddings) - 1):
                similarity = embedding_service.calculate_cosine_similarity(
                    embeddings[i],
                    embeddings[i + 1]
                )
                similarities.append(similarity)

            # Average similarity as coherence
            avg_similarity = sum(similarities) / len(similarities)

            # Convert to 0-100 scale
            # Similarity of 0.7+ is good, 0.5-0.7 is moderate, <0.5 is poor
            coherence_score = min(100, max(0, (avg_similarity - 0.3) * 142.86))

            logger.debug(
                f"Coherence: avg_similarity={avg_similarity:.3f}, "
                f"score={coherence_score:.1f}"
            )

            return coherence_score

        except Exception as e:
            logger.error(f"Error calculating coherence: {str(e)}")
            return 50.0  # Neutral score on error

    async def calculate_progress(
        self,
        messages: List[Dict]
    ) -> float:
        """
        Calculate progress score based on conversation advancement

        Args:
            messages: List of message dicts

        Returns:
            Progress score (0-100)
        """
        try:
            if not messages:
                return 0.0

            # Factors indicating progress:
            # 1. Growing message length (agents elaborating)
            # 2. Diverse vocabulary (not repeating same words)
            # 3. Multiple agents participating (not monologue)
            # 4. Time distribution (steady pacing)

            # Factor 1: Message length progression
            message_lengths = [len(msg["content"]) for msg in messages]
            avg_length = sum(message_lengths) / len(message_lengths)
            length_variance = sum((l - avg_length) ** 2 for l in message_lengths) / len(message_lengths)

            # Good progress: messages between 100-1000 chars with some variance
            length_score = min(100, (avg_length / 10) + (length_variance ** 0.5) / 5)

            # Factor 2: Vocabulary diversity
            all_words = []
            for msg in messages:
                words = msg["content"].lower().split()
                all_words.extend(words)

            if all_words:
                unique_ratio = len(set(all_words)) / len(all_words)
                diversity_score = unique_ratio * 100
            else:
                diversity_score = 0

            # Factor 3: Agent participation
            unique_agents = len(set(msg["agent_name"] for msg in messages))
            total_agents = len(set(msg["agent_name"] for msg in messages))  # Could get from context
            participation_score = min(100, (unique_agents / max(1, total_agents)) * 100)

            # Weighted average
            progress_score = (
                length_score * 0.3 +
                diversity_score * 0.4 +
                participation_score * 0.3
            )

            logger.debug(
                f"Progress: length={length_score:.1f}, "
                f"diversity={diversity_score:.1f}, "
                f"participation={participation_score:.1f}, "
                f"total={progress_score:.1f}"
            )

            return min(100, max(0, progress_score))

        except Exception as e:
            logger.error(f"Error calculating progress: {str(e)}")
            return 50.0  # Neutral score on error

    async def calculate_productivity(
        self,
        messages: List[Dict]
    ) -> float:
        """
        Calculate productivity score based on conversation efficiency

        Args:
            messages: List of message dicts with 'timestamp'

        Returns:
            Productivity score (0-100)
        """
        try:
            if len(messages) < 2:
                return 100.0  # Single message is maximally productive

            # Factors indicating productivity:
            # 1. Response times (not too fast, not too slow)
            # 2. Message density (substantive content)
            # 3. No excessive back-and-forth without progress

            # Factor 1: Response timing
            timestamps = [msg.get("timestamp") for msg in messages if msg.get("timestamp")]

            if len(timestamps) >= 2:
                # Calculate time gaps (assuming timestamps are datetime objects)
                time_gaps = []
                for i in range(len(timestamps) - 1):
                    if isinstance(timestamps[i], datetime) and isinstance(timestamps[i + 1], datetime):
                        gap = (timestamps[i + 1] - timestamps[i]).total_seconds()
                        time_gaps.append(gap)

                if time_gaps:
                    avg_gap = sum(time_gaps) / len(time_gaps)
                    # Ideal: 30-120 seconds between messages
                    if 30 <= avg_gap <= 120:
                        timing_score = 100
                    elif avg_gap < 30:
                        timing_score = 70  # Too fast, possibly superficial
                    elif avg_gap <= 300:
                        timing_score = 80  # Reasonable
                    else:
                        timing_score = 60  # Too slow
                else:
                    timing_score = 75
            else:
                timing_score = 75  # Neutral if no timestamp data

            # Factor 2: Message density (words per message)
            word_counts = [len(msg["content"].split()) for msg in messages]
            avg_words = sum(word_counts) / len(word_counts)

            # Ideal: 50-200 words per message
            if 50 <= avg_words <= 200:
                density_score = 100
            elif avg_words < 50:
                density_score = max(50, avg_words)  # Penalize very short
            else:
                density_score = max(70, 100 - (avg_words - 200) / 10)  # Penalize very long

            # Factor 3: Turn efficiency (not too many turns with same agents)
            agent_sequence = [msg["agent_name"] for msg in messages]
            consecutive_same = 0
            for i in range(len(agent_sequence) - 1):
                if agent_sequence[i] == agent_sequence[i + 1]:
                    consecutive_same += 1

            efficiency_ratio = 1 - (consecutive_same / max(1, len(agent_sequence)))
            efficiency_score = efficiency_ratio * 100

            # Weighted average
            productivity_score = (
                timing_score * 0.3 +
                density_score * 0.4 +
                efficiency_score * 0.3
            )

            logger.debug(
                f"Productivity: timing={timing_score:.1f}, "
                f"density={density_score:.1f}, "
                f"efficiency={efficiency_score:.1f}, "
                f"total={productivity_score:.1f}"
            )

            return min(100, max(0, productivity_score))

        except Exception as e:
            logger.error(f"Error calculating productivity: {str(e)}")
            return 50.0  # Neutral score on error

    def _determine_status(self, overall_score: float) -> str:
        """
        Determine status string from overall score

        Args:
            overall_score: Overall health score (0-100)

        Returns:
            Status string: "excellent", "good", "fair", or "poor"
        """
        if overall_score >= self.excellent_threshold:
            return "excellent"
        elif overall_score >= self.good_threshold:
            return "good"
        elif overall_score >= self.fair_threshold:
            return "fair"
        else:
            return "poor"

    def _create_default_score(self, conversation_id: str) -> HealthScore:
        """Create default health score for empty conversation"""
        return HealthScore(
            conversation_id=conversation_id,
            overall_score=50.0,
            coherence_score=50.0,
            progress_score=50.0,
            productivity_score=50.0,
            status="fair",
            details={"message_count": 0, "reason": "No messages to analyze"}
        )

    async def _store_health_score(
        self,
        db: AsyncSession,
        health_score: HealthScore
    ) -> None:
        """
        Store health score in database

        Args:
            db: Database session
            health_score: HealthScore object to store
        """
        try:
            # Map our scores to the database schema
            # health_score = overall_score
            # coherence_score maps directly
            # contradiction_score = 100 - (contradiction count would be from another service)
            # loop_score = 100 - (loop count would be from another service)
            # citation_score = not yet calculated
            import json
            import uuid

            query = text("""
                INSERT INTO conversation_quality (
                    id,
                    conversation_id,
                    health_score,
                    coherence_score,
                    contradiction_score,
                    loop_score,
                    citation_score,
                    message_count,
                    analysis_metadata,
                    created_at
                )
                VALUES (
                    :id,
                    :conversation_id,
                    :health_score,
                    :coherence_score,
                    :contradiction_score,
                    :loop_score,
                    :citation_score,
                    :message_count,
                    :analysis_metadata,
                    :created_at
                )
            """)

            # Prepare metadata including our additional scores
            analysis_metadata = {
                **health_score.details,
                "status": health_score.status,
                "progress_score": health_score.progress_score,
                "productivity_score": health_score.productivity_score
            }

            await db.execute(
                query,
                {
                    "id": str(uuid.uuid4()),
                    "conversation_id": health_score.conversation_id,
                    "health_score": health_score.overall_score,
                    "coherence_score": health_score.coherence_score,
                    "contradiction_score": 100.0,  # Default, will be updated by contradiction service
                    "loop_score": 100.0,  # Default, will be updated by loop service
                    "citation_score": 100.0,  # Default, not yet implemented
                    "message_count": health_score.details.get("message_count", 0),
                    "analysis_metadata": json.dumps(analysis_metadata),
                    "created_at": health_score.calculated_at
                }
            )
            await db.commit()

            logger.debug(f"Stored health score for conversation {health_score.conversation_id}")

        except Exception as e:
            logger.error(f"Error storing health score: {str(e)}")
            await db.rollback()
            raise


# Singleton instance
health_scoring_service = HealthScoringService()
