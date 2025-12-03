"""
Sequential Debate Service - Orchestrates turn-based multi-LLM debates
Phase 2 implementation: Sequential turn-taking without AI judge.
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
import logging

logger = logging.getLogger(__name__)


class SequentialDebateService:
    """Service for managing sequential turn-based debates"""

    def __init__(self):
        # In-memory storage (could be replaced with database)
        self.debates: Dict[str, DebateV2] = {}

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
        Build conversation context for current participant

        Args:
            debate: Debate instance
            participant: Current participant

        Returns:
            List of messages for LLM (system + user + previous responses)
        """
        messages = []

        # System prompt
        messages.append({
            "role": "system",
            "content": participant.system_prompt
        })

        # User message with topic
        messages.append({
            "role": "user",
            "content": f"Topic: {debate.config.topic}\n\nPlease provide your response to this topic. Consider any previous arguments if this is not the first round."
        })

        # Add previous responses in chronological order (all rounds, all participants)
        for round_obj in debate.rounds:
            for response in round_obj.responses:
                messages.append({
                    "role": "assistant",
                    "content": f"[{response.participant_name}]: {response.content}"
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

        # Stream LLM response
        accumulated_content = ""
        start_time = time.time()
        output_tokens = 0

        try:
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
            logger.error(f"Error streaming from LLM: {str(e)}")
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

        # Advance turn
        debate.advance_turn()

        # Check if round is complete
        if debate.current_turn == 0 and debate.current_round > current_round_num:
            # Round just completed, create next round if needed
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

            # Create next round if not complete
            if not debate.is_debate_complete():
                debate.rounds.append(DebateRoundV2(
                    round_number=debate.current_round,
                    responses=[],
                    tokens_used={},
                    cost_estimate=0.0
                ))

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

        debate.updated_at = datetime.now()

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
