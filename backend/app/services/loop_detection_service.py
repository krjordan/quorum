"""
Loop Detection Service - Identifies repetitive conversation patterns

This service:
- Detects when agents repeat similar arguments or patterns
- Uses pattern fingerprinting with SHA256 hashing
- Generates intervention text to break loops
"""
import logging
import hashlib
from typing import List, Dict, Optional
from datetime import datetime
from collections import deque, Counter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


class ConversationLoop:
    """Data class for detected conversation loop"""

    def __init__(
        self,
        conversation_id: str,
        pattern: str,
        pattern_fingerprint: str,
        message_ids: List[str],
        repetition_count: int,
        agents_involved: List[str],
        intervention_text: Optional[str] = None,
        detected_at: Optional[datetime] = None
    ):
        self.conversation_id = conversation_id
        self.pattern = pattern
        self.pattern_fingerprint = pattern_fingerprint
        self.message_ids = message_ids
        self.repetition_count = repetition_count
        self.agents_involved = agents_involved
        self.intervention_text = intervention_text
        self.detected_at = detected_at or datetime.now()

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "conversation_id": self.conversation_id,
            "pattern": self.pattern,
            "pattern_fingerprint": self.pattern_fingerprint,
            "message_ids": self.message_ids,
            "repetition_count": self.repetition_count,
            "agents_involved": self.agents_involved,
            "intervention_text": self.intervention_text,
            "detected_at": self.detected_at.isoformat()
        }


class LoopDetectionService:
    """Service for detecting repetitive conversation patterns"""

    def __init__(self):
        """Initialize loop detection service"""
        self.min_pattern_length = 2      # Minimum messages in a pattern
        self.min_repetitions = 2         # Minimum repetitions to trigger detection
        self.lookback_window = 20        # Number of recent messages to analyze

    async def detect_loops(
        self,
        db: AsyncSession,
        conversation_id: str,
        recent_messages: List[Dict]
    ) -> Optional[ConversationLoop]:
        """
        Detect repetitive patterns in conversation

        Args:
            db: Database session
            conversation_id: Conversation identifier
            recent_messages: List of recent message dicts with 'id', 'agent_name', 'content'

        Returns:
            ConversationLoop if detected, None otherwise

        Raises:
            Exception: If detection fails
        """
        try:
            if len(recent_messages) < self.min_pattern_length * self.min_repetitions:
                logger.debug("Not enough messages to detect loops")
                return None

            logger.debug(f"Analyzing {len(recent_messages)} messages for loops")

            # Extract agent sequence pattern
            agent_sequence = [msg["agent_name"] for msg in recent_messages]

            # Try different pattern lengths (from longer to shorter for best detection)
            for pattern_length in range(
                min(len(agent_sequence) // 2, 6),  # Max pattern length of 6
                self.min_pattern_length - 1,
                -1
            ):
                loop = await self._detect_pattern_repetition(
                    db=db,
                    conversation_id=conversation_id,
                    messages=recent_messages,
                    agent_sequence=agent_sequence,
                    pattern_length=pattern_length
                )

                if loop:
                    logger.info(
                        f"Detected loop in conversation {conversation_id}: "
                        f"{loop.repetition_count} repetitions of pattern '{loop.pattern}'"
                    )
                    return loop

            logger.debug("No loops detected")
            return None

        except Exception as e:
            logger.error(f"Error detecting loops: {str(e)}")
            raise

    async def _detect_pattern_repetition(
        self,
        db: AsyncSession,
        conversation_id: str,
        messages: List[Dict],
        agent_sequence: List[str],
        pattern_length: int
    ) -> Optional[ConversationLoop]:
        """
        Detect repetition of a specific pattern length

        Args:
            db: Database session
            conversation_id: Conversation identifier
            messages: List of message dicts
            agent_sequence: List of agent names in order
            pattern_length: Length of pattern to check

        Returns:
            ConversationLoop if pattern repetition detected, None otherwise
        """
        if len(agent_sequence) < pattern_length * self.min_repetitions:
            return None

        # Extract all patterns of this length
        patterns = []
        for i in range(len(agent_sequence) - pattern_length + 1):
            pattern = tuple(agent_sequence[i:i + pattern_length])
            patterns.append((i, pattern))

        # Count pattern occurrences
        pattern_counts = Counter([p for _, p in patterns])

        # Find most common pattern with minimum repetitions
        for pattern, count in pattern_counts.most_common():
            if count >= self.min_repetitions:
                # Found a repeating pattern
                pattern_str = " -> ".join(pattern)

                # Get message IDs involved in this pattern
                message_ids = []
                agents_involved = list(set(pattern))

                for idx, p in patterns:
                    if p == pattern:
                        # Add message IDs for this pattern occurrence
                        for offset in range(pattern_length):
                            if idx + offset < len(messages):
                                message_ids.append(messages[idx + offset]["id"])

                # Create pattern fingerprint
                fingerprint = self.create_pattern_fingerprint(messages[-len(message_ids):])

                # Generate intervention text
                intervention = await self.generate_loop_intervention(
                    pattern_str=pattern_str,
                    repetition_count=count,
                    messages=[m for m in messages if m["id"] in message_ids]
                )

                # Create loop object
                loop = ConversationLoop(
                    conversation_id=conversation_id,
                    pattern=pattern_str,
                    pattern_fingerprint=fingerprint,
                    message_ids=message_ids,
                    repetition_count=count,
                    agents_involved=agents_involved,
                    intervention_text=intervention
                )

                # Store in database
                await self._store_loop(db, loop)

                return loop

        return None

    def create_pattern_fingerprint(self, messages: List[Dict]) -> str:
        """
        Create SHA256 fingerprint of conversation pattern

        Args:
            messages: List of message dicts with 'agent_name' and 'content'

        Returns:
            SHA256 hash as hex string
        """
        # Create normalized representation
        pattern_data = []
        for msg in messages:
            # Use agent name + first 100 chars of content for fingerprint
            content_snippet = msg["content"][:100].strip().lower()
            pattern_data.append(f"{msg['agent_name']}:{content_snippet}")

        pattern_string = "|".join(pattern_data)

        # Generate SHA256 hash
        fingerprint = hashlib.sha256(pattern_string.encode()).hexdigest()

        logger.debug(f"Generated fingerprint: {fingerprint[:16]}...")
        return fingerprint

    async def generate_loop_intervention(
        self,
        pattern_str: str,
        repetition_count: int,
        messages: List[Dict]
    ) -> str:
        """
        Generate intervention text to break the loop using LLM

        Args:
            pattern_str: String representation of the pattern
            repetition_count: Number of times pattern repeated
            messages: Messages involved in the loop

        Returns:
            Intervention text to inject into conversation
        """
        try:
            # Extract key points from looping messages
            message_summaries = []
            for i, msg in enumerate(messages[:6]):  # Limit to first 6 messages
                summary = msg["content"][:150] + "..." if len(msg["content"]) > 150 else msg["content"]
                message_summaries.append(f"{msg['agent_name']}: {summary}")

            prompt = f"""A conversation has entered a repetitive loop. The pattern "{pattern_str}" has repeated {repetition_count} times.

Recent messages in the loop:
{chr(10).join(message_summaries)}

Generate a brief, constructive intervention message (2-3 sentences) that:
1. Acknowledges the repetition
2. Suggests a new angle or approach
3. Encourages moving forward productively

Intervention:"""

            system_message = {
                "role": "system",
                "content": "You are a facilitator helping conversations avoid repetitive patterns."
            }

            user_message = {
                "role": "user",
                "content": prompt
            }

            intervention = await llm_service.get_completion(
                [system_message, user_message],
                model="gpt-4o-mini"
            )

            return intervention.strip()

        except Exception as e:
            logger.error(f"Error generating loop intervention: {str(e)}")
            # Fallback intervention
            return (
                f"The conversation appears to be repeating the pattern '{pattern_str}'. "
                f"Let's explore a different angle or approach to move forward productively."
            )

    async def _store_loop(
        self,
        db: AsyncSession,
        loop: ConversationLoop
    ) -> None:
        """
        Store detected loop in database

        Args:
            db: Database session
            loop: ConversationLoop object to store
        """
        try:
            query = text("""
                INSERT INTO conversation_loops (
                    conversation_id,
                    pattern,
                    pattern_fingerprint,
                    message_ids,
                    repetition_count,
                    agents_involved,
                    intervention_text,
                    detected_at
                )
                VALUES (
                    :conversation_id,
                    :pattern,
                    :pattern_fingerprint,
                    :message_ids,
                    :repetition_count,
                    :agents_involved,
                    :intervention_text,
                    :detected_at
                )
            """)

            await db.execute(
                query,
                {
                    "conversation_id": loop.conversation_id,
                    "pattern": loop.pattern,
                    "pattern_fingerprint": loop.pattern_fingerprint,
                    "message_ids": loop.message_ids,
                    "repetition_count": loop.repetition_count,
                    "agents_involved": loop.agents_involved,
                    "intervention_text": loop.intervention_text,
                    "detected_at": loop.detected_at
                }
            )
            await db.commit()

            logger.debug(f"Stored loop detection for conversation {loop.conversation_id}")

        except Exception as e:
            logger.error(f"Error storing loop: {str(e)}")
            await db.rollback()
            raise


# Singleton instance
loop_detection_service = LoopDetectionService()
