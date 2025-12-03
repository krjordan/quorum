"""
Debate Orchestration Service - Coordinates multi-LLM debates with parallel execution
"""
import asyncio
import uuid
import time
import logging
from typing import AsyncGenerator, Dict, List, Tuple
from datetime import datetime

from app.models.debate import (
    Debate, DebateConfig, DebateRound, DebaterResponse,
    DebateStatus, DebateStreamEvent, ParticipantConfig
)
from app.services.llm_service import llm_service
from app.services.context_manager import context_manager
from app.services.judge_service import judge_service
from app.utils.token_counter import token_counter

logger = logging.getLogger(__name__)


class DebateService:
    """Orchestrates multi-LLM debates with parallel execution"""

    def __init__(self):
        self.active_debates: Dict[str, Debate] = {}

    def create_debate(self, config: DebateConfig) -> Debate:
        """
        Create a new debate

        Args:
            config: Debate configuration

        Returns:
            Initialized Debate object
        """
        debate_id = f"debate_{uuid.uuid4().hex[:12]}"

        debate = Debate(
            id=debate_id,
            config=config,
            status=DebateStatus.INITIALIZED,
            rounds=[],
            current_round=0,
            total_tokens={},
            total_cost=0.0
        )

        self.active_debates[debate_id] = debate
        logger.info(f"Created debate {debate_id}: {config.topic}")

        return debate

    def get_debate(self, debate_id: str) -> Debate:
        """Get debate by ID"""
        if debate_id not in self.active_debates:
            raise ValueError(f"Debate {debate_id} not found")
        return self.active_debates[debate_id]

    async def orchestrate_round(self, debate_id: str) -> DebateRound:
        """
        Orchestrate a single debate round with parallel LLM calls

        Args:
            debate_id: Debate identifier

        Returns:
            Completed DebateRound
        """
        debate = self.get_debate(debate_id)
        debate.current_round += 1
        round_number = debate.current_round

        logger.info(f"Starting round {round_number} for debate {debate_id}")

        # Update status
        debate.status = DebateStatus.RUNNING

        # Orchestrate responses in parallel
        responses = await self._orchestrate_parallel_responses(debate, round_number)

        # Calculate round metrics
        tokens_used = {}
        total_round_tokens = 0

        for response in responses:
            if response.model not in tokens_used:
                tokens_used[response.model] = 0
            tokens_used[response.model] += response.tokens_used
            total_round_tokens += response.tokens_used

        # Estimate cost for this round
        round_cost = 0.0
        for model, tokens in tokens_used.items():
            # Rough estimate: assume 50/50 input/output split
            cost = token_counter.estimate_cost(
                input_tokens=tokens // 2,
                output_tokens=tokens // 2,
                model=model
            )
            round_cost += cost

        # Create round object
        debate_round = DebateRound(
            round_number=round_number,
            responses=responses,
            judge_assessment=None,  # Will be added by judge
            tokens_used=tokens_used,
            cost_estimate=round_cost
        )

        # Get judge assessment
        try:
            assessment = await judge_service.assess_round(
                config=debate.config,
                round_data=debate_round,
                all_rounds=debate.rounds
            )
            debate_round.judge_assessment = assessment
        except Exception as e:
            logger.error(f"Error getting judge assessment: {e}", exc_info=True)

        # Update debate state
        debate.rounds.append(debate_round)

        # Update totals
        for model, tokens in tokens_used.items():
            if model not in debate.total_tokens:
                debate.total_tokens[model] = 0
            debate.total_tokens[model] += tokens

        debate.total_cost += round_cost
        debate.updated_at = datetime.now()

        # Check if debate should continue
        if debate_round.judge_assessment and not debate_round.judge_assessment.should_continue:
            await self._finalize_debate(debate)

        logger.info(f"Completed round {round_number} - Cost: ${round_cost:.4f}, Total: ${debate.total_cost:.4f}")

        return debate_round

    async def _orchestrate_parallel_responses(
        self,
        debate: Debate,
        round_number: int
    ) -> List[DebaterResponse]:
        """
        Orchestrate parallel LLM calls for all participants

        Args:
            debate: Debate object
            round_number: Current round number

        Returns:
            List of DebaterResponse objects
        """
        logger.info(f"Orchestrating parallel responses from {len(debate.config.participants)} participants")

        # Create tasks for each participant
        tasks = []
        for participant in debate.config.participants:
            task = self._get_participant_response(debate, participant, round_number)
            tasks.append(task)

        # Execute in parallel
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        valid_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                participant = debate.config.participants[i]
                logger.error(f"Error from {participant.persona.name}: {response}")
                # Create error response
                error_response = DebaterResponse(
                    participant_name=participant.persona.name,
                    model=participant.model,
                    content=f"[Error generating response: {str(response)}]",
                    tokens_used=0,
                    response_time_ms=0
                )
                valid_responses.append(error_response)
            else:
                valid_responses.append(response)

        return valid_responses

    async def _get_participant_response(
        self,
        debate: Debate,
        participant: ParticipantConfig,
        round_number: int
    ) -> DebaterResponse:
        """
        Get response from a single participant

        Args:
            debate: Debate object
            participant: Participant configuration
            round_number: Current round number

        Returns:
            DebaterResponse
        """
        start_time = time.time()

        # Build context
        messages, context_tokens = context_manager.build_context(
            config=debate.config,
            rounds=debate.rounds,
            participant=participant
        )

        # Get completion
        try:
            content = await llm_service.get_completion(
                messages=messages,
                model=participant.model
            )

            # Count tokens
            output_tokens = token_counter.count_tokens(content, participant.model)
            total_tokens = context_tokens + output_tokens

            response_time_ms = (time.time() - start_time) * 1000

            response = DebaterResponse(
                participant_name=participant.persona.name,
                model=participant.model,
                content=content,
                tokens_used=total_tokens,
                response_time_ms=response_time_ms
            )

            logger.info(
                f"Response from {participant.persona.name} ({participant.model}): "
                f"{len(content)} chars, {total_tokens} tokens, {response_time_ms:.0f}ms"
            )

            return response

        except Exception as e:
            logger.error(f"Error getting response from {participant.persona.name}: {e}", exc_info=True)
            raise

    async def stream_debate_responses(self, debate_id: str) -> AsyncGenerator[DebateStreamEvent, None]:
        """
        Stream debate responses in real-time using SSE

        Args:
            debate_id: Debate identifier

        Yields:
            DebateStreamEvent objects
        """
        debate = self.get_debate(debate_id)

        try:
            while debate.status in [DebateStatus.INITIALIZED, DebateStatus.RUNNING]:
                round_number = debate.current_round + 1

                # Emit round start
                yield DebateStreamEvent(
                    event_type="round_start",
                    debate_id=debate_id,
                    round_number=round_number,
                    data={
                        "topic": debate.config.topic,
                        "participants": [p.persona.name for p in debate.config.participants]
                    }
                )

                # Orchestrate round (parallel responses)
                debate_round = await self.orchestrate_round(debate_id)

                # Stream each response
                for response in debate_round.responses:
                    yield DebateStreamEvent(
                        event_type="response",
                        debate_id=debate_id,
                        round_number=round_number,
                        data={
                            "participant": response.participant_name,
                            "model": response.model,
                            "content": response.content,
                            "tokens": response.tokens_used,
                            "response_time_ms": response.response_time_ms
                        }
                    )

                # Stream judge assessment
                if debate_round.judge_assessment:
                    yield DebateStreamEvent(
                        event_type="judge_assessment",
                        debate_id=debate_id,
                        round_number=round_number,
                        data={
                            "rubric_scores": debate_round.judge_assessment.rubric_scores,
                            "participant_scores": debate_round.judge_assessment.participant_scores,
                            "analysis": debate_round.judge_assessment.analysis,
                            "should_continue": debate_round.judge_assessment.should_continue,
                            "stopping_reason": debate_round.judge_assessment.stopping_reason
                        }
                    )

                # Emit round end with metrics
                yield DebateStreamEvent(
                    event_type="round_end",
                    debate_id=debate_id,
                    round_number=round_number,
                    data={
                        "tokens_used": debate_round.tokens_used,
                        "cost_estimate": debate_round.cost_estimate,
                        "total_cost": debate.total_cost
                    }
                )

                # Check cost warnings
                cost_warning = context_manager.check_cost_warning(
                    total_cost=debate.total_cost,
                    threshold=debate.config.cost_warning_threshold
                )

                if cost_warning["should_warn"]:
                    yield DebateStreamEvent(
                        event_type="cost_warning",
                        debate_id=debate_id,
                        round_number=round_number,
                        data=cost_warning
                    )

                # Check if debate should continue
                if debate_round.judge_assessment and not debate_round.judge_assessment.should_continue:
                    break

                # Small delay between rounds
                await asyncio.sleep(0.5)

            # Emit debate end
            yield DebateStreamEvent(
                event_type="debate_end",
                debate_id=debate_id,
                round_number=debate.current_round,
                data={
                    "status": debate.status.value,
                    "total_rounds": len(debate.rounds),
                    "total_cost": debate.total_cost,
                    "winner": debate.winner,
                    "final_verdict": debate.final_verdict
                }
            )

        except Exception as e:
            logger.error(f"Error streaming debate {debate_id}: {e}", exc_info=True)
            debate.status = DebateStatus.ERROR

            yield DebateStreamEvent(
                event_type="error",
                debate_id=debate_id,
                round_number=debate.current_round,
                data={
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )

    async def _finalize_debate(self, debate: Debate):
        """
        Finalize debate and generate final verdict

        Args:
            debate: Debate to finalize
        """
        logger.info(f"Finalizing debate {debate.id}")

        debate.status = DebateStatus.COMPLETED

        # Generate final verdict
        try:
            winner, verdict = await judge_service.generate_final_verdict(
                config=debate.config,
                all_rounds=debate.rounds
            )
            debate.winner = winner
            debate.final_verdict = verdict
        except Exception as e:
            logger.error(f"Error generating final verdict: {e}", exc_info=True)
            debate.winner = "No winner"
            debate.final_verdict = f"Error generating verdict: {str(e)}"

        debate.updated_at = datetime.now()

    def export_debate(self, debate_id: str, format: str = "markdown") -> str:
        """
        Export debate in specified format

        Args:
            debate_id: Debate identifier
            format: Export format (markdown, json, html)

        Returns:
            Formatted debate string
        """
        debate = self.get_debate(debate_id)

        if format == "json":
            return debate.model_dump_json(indent=2)
        elif format == "markdown":
            return self._export_markdown(debate)
        elif format == "html":
            return self._export_html(debate)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _export_markdown(self, debate: Debate) -> str:
        """Export debate as Markdown"""
        lines = [
            f"# Debate: {debate.config.topic}",
            f"\n**Status**: {debate.status.value}",
            f"**Rounds**: {len(debate.rounds)}",
            f"**Total Cost**: ${debate.total_cost:.4f}",
            f"\n## Participants\n"
        ]

        for participant in debate.config.participants:
            lines.append(f"- **{participant.persona.name}** ({participant.model}): {participant.persona.role}")

        lines.append("\n## Debate Transcript\n")

        for round_data in debate.rounds:
            lines.append(f"### Round {round_data.round_number}\n")

            for response in round_data.responses:
                lines.append(f"**{response.participant_name}**:\n\n{response.content}\n")

            if round_data.judge_assessment:
                lines.append(f"\n**Judge Assessment**:\n\n{round_data.judge_assessment.analysis}\n")
                lines.append(f"\n**Scores**: {round_data.judge_assessment.participant_scores}\n")

        if debate.final_verdict:
            lines.append(f"\n## Final Verdict\n")
            lines.append(f"**Winner**: {debate.winner}\n")
            lines.append(f"\n{debate.final_verdict}\n")

        return "\n".join(lines)

    def _export_html(self, debate: Debate) -> str:
        """Export debate as HTML"""
        html_parts = [
            "<!DOCTYPE html>",
            "<html><head>",
            f"<title>{debate.config.topic}</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 20px; }",
            "h1 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }",
            ".round { background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 8px; }",
            ".response { margin: 15px 0; }",
            ".participant { font-weight: bold; color: #007bff; }",
            ".judge { background: #fff3cd; padding: 15px; margin: 15px 0; border-left: 4px solid #ffc107; }",
            "</style>",
            "</head><body>",
            f"<h1>{debate.config.topic}</h1>",
            f"<p><strong>Status:</strong> {debate.status.value}</p>",
            f"<p><strong>Total Cost:</strong> ${debate.total_cost:.4f}</p>",
        ]

        for round_data in debate.rounds:
            html_parts.append(f'<div class="round">')
            html_parts.append(f'<h2>Round {round_data.round_number}</h2>')

            for response in round_data.responses:
                html_parts.append(f'<div class="response">')
                html_parts.append(f'<span class="participant">{response.participant_name}</span>')
                html_parts.append(f'<p>{response.content}</p>')
                html_parts.append('</div>')

            if round_data.judge_assessment:
                html_parts.append(f'<div class="judge">')
                html_parts.append(f'<strong>Judge Assessment:</strong>')
                html_parts.append(f'<p>{round_data.judge_assessment.analysis}</p>')
                html_parts.append('</div>')

            html_parts.append('</div>')

        if debate.final_verdict:
            html_parts.append('<div class="judge">')
            html_parts.append(f'<h2>Final Verdict</h2>')
            html_parts.append(f'<p><strong>Winner:</strong> {debate.winner}</p>')
            html_parts.append(f'<p>{debate.final_verdict}</p>')
            html_parts.append('</div>')

        html_parts.append("</body></html>")
        return "\n".join(html_parts)


# Singleton instance
debate_service = DebateService()
