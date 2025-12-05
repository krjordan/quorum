"""
Sequential Debate Service - Orchestrates turn-based multi-LLM debates
Phase 2 implementation: Sequential turn-taking without AI judge.
Phase 3: Integrated conversation quality management
"""
import uuid
import time
from typing import AsyncGenerator, Dict, List, Optional
from datetime import datetime
from app.models.debate_v2 import (
    DebateV2,
    DebateConfigV2,
    DebateStatusV2,
    DebateRoundV2,
    ParticipantResponse,
    SequentialTurnEvent,
    SequentialTurnEventType,
    ParticipantConfigV2
)
from app.services.llm_service import llm_service
from app.utils.token_counter import token_counter
from app.services.embedding_service import embedding_service
from app.services.contradiction_service import contradiction_service
from app.services.loop_detection_service import loop_detection_service
from app.services.health_scoring_service import health_scoring_service
from app.config.database import get_async_session
from app.models.quality import Conversation, Message
import logging

logger = logging.getLogger(__name__)


class SequentialDebateService:
    """Service for managing sequential turn-based debates"""

    def __init__(self):
        # In-memory storage (could be replaced with database)
        self.debates: Dict[str, DebateV2] = {}
        # Track database conversation IDs
        self.debate_to_conversation: Dict[str, str] = {}

    def create_debate(self, config: DebateConfigV2) -> DebateV2:
        """
        Create a new sequential debate

        Args:
            config: Debate configuration

        Returns:
            Initialized DebateV2 instance
        """
        debate_id = f"debate_v2_{uuid.uuid4().hex[:12]}"

        debate = DebateV2(
            id=debate_id,
            config=config,
            status=DebateStatusV2.INITIALIZED,
            current_round=1,
            current_turn=0,
            total_tokens={},
            total_cost=0.0
        )

        # Initialize first round
        debate.rounds.append(DebateRoundV2(
            round_number=1,
            responses=[],
            tokens_used={},
            cost_estimate=0.0
        ))

        self.debates[debate_id] = debate
        logger.info(f"Created debate {debate_id} with {len(config.participants)} participants, {config.max_rounds} rounds")

        return debate

    def get_debate(self, debate_id: str) -> Optional[DebateV2]:
        """Get debate by ID"""
        return self.debates.get(debate_id)

    def stop_debate(self, debate_id: str) -> DebateV2:
        """
        Manually stop a debate

        Args:
            debate_id: Debate identifier

        Returns:
            Updated debate

        Raises:
            ValueError: If debate not found
        """
        debate = self.debates.get(debate_id)
        if not debate:
            raise ValueError(f"Debate {debate_id} not found")

        debate.status = DebateStatusV2.STOPPED
        debate.stopped_manually = True
        debate.updated_at = datetime.now()

        logger.info(f"Debate {debate_id} stopped manually at round {debate.current_round}, turn {debate.current_turn}")

        return debate

    def pause_debate(self, debate_id: str) -> DebateV2:
        """Pause a running debate"""
        debate = self.debates.get(debate_id)
        if not debate:
            raise ValueError(f"Debate {debate_id} not found")

        debate.status = DebateStatusV2.PAUSED
        debate.updated_at = datetime.now()

        logger.info(f"Debate {debate_id} paused")

        return debate

    def resume_debate(self, debate_id: str) -> DebateV2:
        """Resume a paused debate"""
        debate = self.debates.get(debate_id)
        if not debate:
            raise ValueError(f"Debate {debate_id} not found")

        if debate.status != DebateStatusV2.PAUSED:
            raise ValueError(f"Debate {debate_id} is not paused (status: {debate.status})")

        debate.status = DebateStatusV2.RUNNING
        debate.updated_at = datetime.now()

        logger.info(f"Debate {debate_id} resumed")

        return debate

    def _build_context_for_participant(
        self,
        debate: DebateV2,
        participant: ParticipantConfigV2
    ) -> List[Dict[str, str]]:
        """
        Build conversation context for current participant.

        Anthropic's Messages API (and most chat APIs) expect the final entry
        before the model responds to have role "user". To keep the transcript
        intact while satisfying that contract, we embed the prior debate history
        into a single user message.
        """
        messages = [{
            "role": "system",
            "content": participant.system_prompt
        }]

        user_content_lines = [
            f"Topic: {debate.config.topic}",
            "",
            f"You are {participant.name}. Provide your next debate response.",
            "Be concise, reference earlier arguments when helpful, "
            "and continue the conversation naturally.",
            "",
            "IMPORTANT: Do NOT prefix your response with your name or 'Agent X:'. "
            "Your response should start directly with your argument."
        ]

        transcript_lines = []
        for round_obj in debate.rounds:
            for response in round_obj.responses:
                transcript_lines.append(f"{response.participant_name}: {response.content}")

        if transcript_lines:
            user_content_lines.extend([
                "",
                "Transcript so far:",
                *transcript_lines,
                "",
                "Consider the transcript above when crafting your response."
            ])

        messages.append({
            "role": "user",
            "content": "\n".join(user_content_lines)
        })

        return messages

    async def get_next_turn_response(
        self,
        debate_id: str
    ) -> AsyncGenerator[SequentialTurnEvent, None]:
        """
        Execute next participant's turn and stream the response

        Args:
            debate_id: Debate identifier

        Yields:
            SequentialTurnEvent objects for SSE streaming

        Raises:
            ValueError: If debate not found or invalid state
        """
        debate = self.debates.get(debate_id)
        if not debate:
            raise ValueError(f"Debate {debate_id} not found")

        # Check if debate is complete
        if debate.is_debate_complete():
            yield SequentialTurnEvent(
                event_type=SequentialTurnEventType.DEBATE_COMPLETE,
                debate_id=debate_id,
                round_number=debate.current_round,
                turn_index=debate.current_turn,
                data={
                    "message": "Debate is complete",
                    "rounds_completed": len(debate.rounds),
                    "stopped_manually": debate.stopped_manually
                }
            )
            debate.status = DebateStatusV2.COMPLETED if not debate.stopped_manually else DebateStatusV2.STOPPED
            return

        # Mark debate as running
        if debate.status == DebateStatusV2.INITIALIZED:
            debate.status = DebateStatusV2.RUNNING
            yield SequentialTurnEvent(
                event_type=SequentialTurnEventType.DEBATE_START,
                debate_id=debate_id,
                round_number=debate.current_round,
                turn_index=0,
                data={
                    "topic": debate.config.topic,
                    "participants": [p.name for p in debate.config.participants],
                    "max_rounds": debate.config.max_rounds
                }
            )

        # Get current participant
        participant = debate.get_current_participant()
        current_round_num = debate.current_round
        current_turn_index = debate.current_turn

        logger.info(f"Debate {debate_id}: Round {current_round_num}, Turn {current_turn_index} ({participant.name})")

        # Emit participant_start event
        yield SequentialTurnEvent(
            event_type=SequentialTurnEventType.PARTICIPANT_START,
            debate_id=debate_id,
            round_number=current_round_num,
            turn_index=current_turn_index,
            data={
                "participant_name": participant.name,
                "participant_index": current_turn_index,
                "model": participant.model
            }
        )

        # Build context
        messages = self._build_context_for_participant(debate, participant)

        # Count input tokens
        input_tokens = token_counter.count_message_tokens(messages, participant.model)

        # Get LLM response
        accumulated_content = ""
        start_time = time.time()
        output_tokens = 0

        # Check if model is Claude (LiteLLM streaming broken for Claude)
        is_claude = "claude" in participant.model.lower()

        try:
            if is_claude:
                # Use non-streaming for Claude models
                logger.info(f"Using non-streaming completion for Claude model: {participant.model}")
                accumulated_content = await llm_service.get_completion(messages, participant.model)
                output_tokens = token_counter.count_tokens(accumulated_content, participant.model)
                if accumulated_content:
                    # Emit a single chunk so the frontend receives Claude's reply
                    yield SequentialTurnEvent(
                        event_type=SequentialTurnEventType.CHUNK,
                        debate_id=debate_id,
                        round_number=current_round_num,
                        turn_index=current_turn_index,
                        data={
                            "text": accumulated_content,
                            "participant_name": participant.name
                        }
                    )
            else:
                # Use streaming for other models (GPT, Gemini, etc.)
                async for chunk in llm_service.stream_completion(messages, participant.model):
                    accumulated_content += chunk
                    output_tokens = token_counter.count_tokens(accumulated_content, participant.model)

                    # Emit chunk event
                    yield SequentialTurnEvent(
                        event_type=SequentialTurnEventType.CHUNK,
                        debate_id=debate_id,
                        round_number=current_round_num,
                        turn_index=current_turn_index,
                        data={
                            "text": chunk,
                            "participant_name": participant.name
                        }
                    )

        except Exception as e:
            logger.error(f"Error getting LLM response: {str(e)}")
            yield SequentialTurnEvent(
                event_type=SequentialTurnEventType.ERROR,
                debate_id=debate_id,
                round_number=current_round_num,
                turn_index=current_turn_index,
                data={
                    "error": str(e),
                    "participant_name": participant.name
                }
            )
            debate.status = DebateStatusV2.ERROR
            return

        # Calculate response metrics
        response_time_ms = (time.time() - start_time) * 1000
        total_tokens = input_tokens + output_tokens
        cost = token_counter.estimate_cost(input_tokens, output_tokens, participant.model)

        # Create response object
        response = ParticipantResponse(
            participant_name=participant.name,
            participant_index=current_turn_index,
            model=participant.model,
            content=accumulated_content,
            tokens_used=total_tokens,
            response_time_ms=response_time_ms
        )

        # Update debate state
        current_round = debate.rounds[current_round_num - 1]
        current_round.responses.append(response)

        # Update token/cost tracking
        model_key = participant.model
        if model_key not in current_round.tokens_used:
            current_round.tokens_used[model_key] = 0
        current_round.tokens_used[model_key] += total_tokens

        if model_key not in debate.total_tokens:
            debate.total_tokens[model_key] = 0
        debate.total_tokens[model_key] += total_tokens

        current_round.cost_estimate += cost
        debate.total_cost += cost

        # ===== ADVANCE TURN BEFORE PARTICIPANT_COMPLETE =====
        # CRITICAL: Must happen BEFORE participant_complete because frontend closes
        # the SSE connection on that event, terminating this generator.
        # We also update current_round reference to avoid stale object issues.

        # Calculate next state
        next_turn = debate.current_turn + 1
        next_round = debate.current_round

        if next_turn >= len(debate.config.participants):
            # Completed all participants in this round, advance to next round
            next_turn = 0
            next_round = debate.current_round + 1

        # Create new debate instance with updated state (Pydantic-safe)
        debate_dict = debate.model_dump()
        debate_dict['current_turn'] = next_turn
        debate_dict['current_round'] = next_round
        debate_dict['updated_at'] = datetime.now()

        # If we're advancing to a new round, create the round object in the list
        if next_round > debate.current_round:
            # Create new round object
            new_round = DebateRoundV2(
                round_number=next_round,
                responses=[],
                tokens_used={},
                cost_estimate=0.0,
                timestamp=datetime.now()
            )
            debate_dict['rounds'].append(new_round.model_dump())

        # Replace the entire debate object
        updated_debate = DebateV2(**debate_dict)
        self.debates[debate_id] = updated_debate
        debate = updated_debate

        # Update current_round reference to point to new debate's round object
        # (prevents stale object reference issues)
        current_round = debate.rounds[current_round_num - 1]

        # Emit participant_complete event
        yield SequentialTurnEvent(
            event_type=SequentialTurnEventType.PARTICIPANT_COMPLETE,
            debate_id=debate_id,
            round_number=current_round_num,
            turn_index=current_turn_index,
            data={
                "participant_name": participant.name,
                "tokens_used": total_tokens,
                "cost": cost,
                "response_time_ms": response_time_ms
            }
        )

        # ===== CONVERSATION QUALITY INTEGRATION =====
        logger.info(f"[QUALITY] Starting quality integration for debate {debate_id}, participant {participant.name}")
        try:
            async with get_async_session() as db:
                logger.info(f"[QUALITY] Obtained database session")
                # 1. Ensure conversation exists in database
                conversation_id = self.debate_to_conversation.get(debate_id)
                if not conversation_id:
                    # Create conversation on first message
                    conversation = Conversation(
                        id=debate_id,
                        user_id=None,  # Anonymous for now
                        title=debate.config.topic,
                        topic=debate.config.topic,
                        current_health_score=100.0
                    )
                    db.add(conversation)
                    await db.commit()
                    await db.refresh(conversation)
                    self.debate_to_conversation[debate_id] = conversation.id
                    conversation_id = conversation.id
                    logger.info(f"Created conversation {conversation_id} for debate {debate_id}")

                # 2. Store message in database
                message_id = f"msg_{uuid.uuid4().hex[:12]}"
                sequence_number = sum(len(r.responses) for r in debate.rounds)

                message = Message(
                    id=message_id,
                    conversation_id=conversation_id,
                    agent_name=participant.name,
                    agent_model=participant.model,
                    role="agent",
                    content=accumulated_content,
                    sequence_number=sequence_number,
                    round_number=current_round_num,
                    turn_index=current_turn_index,
                    tokens_used=total_tokens,
                    response_time_ms=response_time_ms,
                    health_score=100.0  # Will be updated by health scoring
                )
                db.add(message)
                await db.commit()
                await db.refresh(message)

                # 3. Generate and store embedding (async, non-blocking for SSE)
                try:
                    embedding = await embedding_service.generate_embedding(accumulated_content)
                    await embedding_service.store_embedding(
                        db=db,
                        message_id=message_id,
                        embedding=embedding,
                        metadata={
                            "conversation_id": conversation_id,
                            "model": "text-embedding-3-small",
                            "participant": participant.name
                        }
                    )
                    logger.debug(f"Stored embedding for message {message_id}")
                except Exception as e:
                    logger.error(f"Error generating embedding: {str(e)}")
                    # Continue anyway - embedding is not critical for streaming

                # 4. Check for contradictions
                try:
                    # Convert Message object to dict for contradiction service
                    message_dict = {
                        "id": message_id,
                        "content": accumulated_content,
                        "agent_name": participant.name
                    }
                    contradictions = await contradiction_service.detect_contradictions(
                        db=db,
                        conversation_id=conversation_id,
                        new_message=message_dict
                    )

                    if contradictions:
                        logger.info(f"Detected {len(contradictions)} contradictions in message {message_id}")
                        for contradiction in contradictions:
                            yield SequentialTurnEvent(
                                event_type=SequentialTurnEventType.QUALITY_UPDATE,
                                debate_id=debate_id,
                                round_number=current_round_num,
                                turn_index=current_turn_index,
                                data={
                                    "quality_type": "contradiction",
                                    "contradiction_id": contradiction.id,
                                    "severity": contradiction.severity.value,
                                    "similarity_score": contradiction.similarity_score,
                                    "explanation": contradiction.explanation
                                }
                            )
                except Exception as e:
                    logger.error(f"Error detecting contradictions: {str(e)}")

                # 5. Check for loops (every 3 messages)
                if sequence_number > 0 and sequence_number % 3 == 0:
                    try:
                        # Convert responses to dicts for loop detection
                        recent_response_dicts = []
                        for resp in current_round.responses[-10:]:
                            recent_response_dicts.append({
                                "id": f"msg_{resp.participant_name}_{resp.timestamp.timestamp() if hasattr(resp, 'timestamp') else ''}",
                                "agent_name": resp.participant_name,
                                "content": resp.content
                            })

                        loop = await loop_detection_service.detect_loops(
                            db=db,
                            conversation_id=conversation_id,
                            recent_messages=recent_response_dicts
                        )

                        if loop:
                            logger.info(f"Loop detected in conversation {conversation_id}: {loop.pattern_fingerprint}")
                            yield SequentialTurnEvent(
                                event_type=SequentialTurnEventType.QUALITY_UPDATE,
                                debate_id=debate_id,
                                round_number=current_round_num,
                                turn_index=current_turn_index,
                                data={
                                    "quality_type": "loop",
                                    "loop_id": loop.id,
                                    "repetition_count": loop.repetition_count,
                                    "intervention_text": loop.intervention_text
                                }
                            )
                    except Exception as e:
                        logger.error(f"Error detecting loops: {str(e)}")

                # 6. Calculate health score (every message)
                try:
                    # Get all responses from debate and convert to dicts
                    all_responses = []
                    for round_obj in debate.rounds:
                        for resp in round_obj.responses:
                            all_responses.append({
                                "id": f"msg_{resp.participant_name}_{resp.timestamp.timestamp() if hasattr(resp, 'timestamp') else ''}",
                                "content": resp.content,
                                "agent_name": resp.participant_name,
                                "timestamp": resp.timestamp if hasattr(resp, 'timestamp') else datetime.now()
                            })

                    # Use last 10 messages for health calculation
                    recent_messages = all_responses[-10:] if len(all_responses) > 10 else all_responses

                    health_score = await health_scoring_service.calculate_health_score(
                        db=db,
                        conversation_id=conversation_id,
                        recent_messages=recent_messages
                    )

                    # Update conversation health score
                    conversation = await db.get(Conversation, conversation_id)
                    if conversation:
                        conversation.current_health_score = health_score.overall_score
                        await db.commit()

                    # Emit health score update
                    yield SequentialTurnEvent(
                        event_type=SequentialTurnEventType.QUALITY_UPDATE,
                        debate_id=debate_id,
                        round_number=current_round_num,
                        turn_index=current_turn_index,
                        data={
                            "quality_type": "health_score",
                            "score": health_score.overall_score,
                            "status": health_score.status,
                            "coherence": health_score.coherence_score,
                            "progress": health_score.progress_score,
                            "productivity": health_score.productivity_score,
                            "details": health_score.details
                        }
                    )

                    logger.info(f"Health score for conversation {conversation_id}: {health_score.overall_score}")

                except Exception as e:
                    logger.error(f"Error calculating health score: {str(e)}")

        except Exception as e:
            # Log but don't fail the debate if quality checks fail
            logger.error(f"Error in quality integration: {str(e)}")
            # Optionally emit an error event
            yield SequentialTurnEvent(
                event_type=SequentialTurnEventType.ERROR,
                debate_id=debate_id,
                round_number=current_round_num,
                turn_index=current_turn_index,
                data={
                    "error": f"Quality check error: {str(e)}",
                    "non_critical": True
                }
            )
        # ===== END QUALITY INTEGRATION =====

        # Emit cost update
        yield SequentialTurnEvent(
            event_type=SequentialTurnEventType.COST_UPDATE,
            debate_id=debate_id,
            round_number=current_round_num,
            turn_index=current_turn_index,
            data={
                "total_cost": debate.total_cost,
                "round_cost": current_round.cost_estimate,
                "total_tokens": debate.total_tokens,
                "warning_threshold": debate.config.cost_warning_threshold
            }
        )

        # Check if round is complete (turn was already advanced earlier)
        if debate.current_turn == 0 and debate.current_round > current_round_num:
            # Round just completed - emit events
            yield SequentialTurnEvent(
                event_type=SequentialTurnEventType.ROUND_COMPLETE,
                debate_id=debate_id,
                round_number=current_round_num,
                turn_index=0,
                data={
                    "round_number": current_round_num,
                    "responses_count": len(current_round.responses),
                    "round_cost": current_round.cost_estimate
                }
            )

            # Emit round_start for the new round (already created when we advanced turn)
            if not debate.is_debate_complete():
                yield SequentialTurnEvent(
                    event_type=SequentialTurnEventType.ROUND_START,
                    debate_id=debate_id,
                    round_number=debate.current_round,
                    turn_index=0,
                    data={
                        "round_number": debate.current_round,
                        "max_rounds": debate.config.max_rounds
                    }
                )

        # Note: debate.updated_at was already set when we advanced the turn earlier

        # Check if debate is now complete
        if debate.is_debate_complete():
            yield SequentialTurnEvent(
                event_type=SequentialTurnEventType.DEBATE_COMPLETE,
                debate_id=debate_id,
                round_number=debate.current_round,
                turn_index=0,
                data={
                    "message": "Debate completed all rounds",
                    "rounds_completed": len(debate.rounds),
                    "total_cost": debate.total_cost
                }
            )
            debate.status = DebateStatusV2.COMPLETED


# Singleton instance
sequential_debate_service = SequentialDebateService()
