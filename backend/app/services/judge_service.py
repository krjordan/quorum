"""
Judge Service - Evaluates debate rounds and determines winners
"""
import json
import logging
from typing import List, Dict, Tuple
from app.models.debate import DebateRound, JudgeAssessment, DebateConfig
from app.services.llm_service import llm_service
from app.utils.token_counter import token_counter

logger = logging.getLogger(__name__)


class JudgeService:
    """Evaluates debate rounds using structured rubric"""

    # Rubric dimensions
    RUBRIC_DIMENSIONS = {
        "argumentation": "Quality of logical reasoning and argument structure",
        "evidence": "Use of evidence, examples, and supporting data",
        "coherence": "Clarity and organization of ideas",
        "engagement": "Direct engagement with opponents' arguments",
        "novelty": "Introduction of new perspectives or insights",
        "persuasiveness": "Overall convincingness and rhetorical effectiveness"
    }

    def __init__(self):
        self.repetition_threshold = 0.7  # 70% similarity triggers repetition warning

    async def assess_round(
        self,
        config: DebateConfig,
        round_data: DebateRound,
        all_rounds: List[DebateRound]
    ) -> JudgeAssessment:
        """
        Assess a debate round using structured rubric

        Args:
            config: Debate configuration
            round_data: Current round to assess
            all_rounds: All previous rounds for context

        Returns:
            JudgeAssessment with scores and continuation decision
        """
        logger.info(f"Assessing round {round_data.round_number}")

        # Build judge prompt
        messages = self._build_judge_prompt(config, round_data, all_rounds)

        # Get structured assessment
        try:
            response = await llm_service.get_completion(
                messages=messages,
                model=config.judge_model
            )

            # Parse JSON response
            assessment_data = self._parse_judge_response(response)

            # Check stopping criteria
            should_continue, stopping_reason = self._check_stopping_criteria(
                config, round_data, all_rounds, assessment_data
            )

            # Build assessment
            assessment = JudgeAssessment(
                round_number=round_data.round_number,
                rubric_scores=assessment_data["rubric_scores"],
                participant_scores=assessment_data["participant_scores"],
                analysis=assessment_data["analysis"],
                should_continue=should_continue,
                stopping_reason=stopping_reason
            )

            logger.info(f"Assessment complete - Continue: {should_continue}")
            return assessment

        except Exception as e:
            logger.error(f"Error assessing round: {e}", exc_info=True)
            # Return default assessment on error
            return self._create_default_assessment(round_data, str(e))

    async def generate_final_verdict(
        self,
        config: DebateConfig,
        all_rounds: List[DebateRound]
    ) -> Tuple[str, str]:
        """
        Generate final verdict for completed debate

        Args:
            config: Debate configuration
            all_rounds: All debate rounds

        Returns:
            Tuple of (winner_name, verdict_text)
        """
        logger.info("Generating final verdict")

        messages = self._build_verdict_prompt(config, all_rounds)

        try:
            response = await llm_service.get_completion(
                messages=messages,
                model=config.judge_model
            )

            verdict_data = self._parse_verdict_response(response)

            return verdict_data["winner"], verdict_data["verdict"]

        except Exception as e:
            logger.error(f"Error generating verdict: {e}", exc_info=True)
            return "No winner", f"Error generating verdict: {str(e)}"

    def _build_judge_prompt(
        self,
        config: DebateConfig,
        round_data: DebateRound,
        all_rounds: List[DebateRound]
    ) -> List[Dict[str, str]]:
        """Build prompt for judge assessment"""

        # System prompt
        system_prompt = f"""You are an expert debate judge evaluating a multi-perspective debate on: "{config.topic}"

Your task is to assess Round {round_data.round_number} using a structured rubric and provide scores and analysis.

Rubric Dimensions (score 0-10 for each):
{self._format_rubric()}

Evaluate each participant's contribution independently, then provide:
1. Rubric scores (0-10) for each dimension, averaged across all participants
2. Individual scores (0-10) for each participant
3. Analytical summary of the round

Respond in JSON format:
{{
  "rubric_scores": {{
    "argumentation": 8.5,
    "evidence": 7.0,
    "coherence": 9.0,
    "engagement": 8.0,
    "novelty": 6.5,
    "persuasiveness": 7.5
  }},
  "participant_scores": {{
    "Participant Name 1": 8.0,
    "Participant Name 2": 7.5
  }},
  "analysis": "Your detailed analysis here..."
}}"""

        # Build round context
        round_context = f"**Round {round_data.round_number}**\n\n"
        for response in round_data.responses:
            round_context += f"**{response.participant_name}** ({response.model}):\n{response.content}\n\n"

        # Add previous round context if available
        context_summary = ""
        if len(all_rounds) > 1:
            prev_round = all_rounds[-2]
            if prev_round.judge_assessment:
                context_summary = f"\n**Previous Round Assessment**:\n{prev_round.judge_assessment.analysis}\n"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context_summary + round_context}
        ]

        return messages

    def _build_verdict_prompt(
        self,
        config: DebateConfig,
        all_rounds: List[DebateRound]
    ) -> List[Dict[str, str]]:
        """Build prompt for final verdict"""

        system_prompt = f"""You are an expert debate judge providing a final verdict for a debate on: "{config.topic}"

Review all {len(all_rounds)} rounds and determine:
1. The winner (participant who made the most compelling case)
2. A comprehensive final verdict explaining your decision

Consider:
- Consistency and strength of arguments throughout the debate
- Effective engagement with opposing viewpoints
- Quality of evidence and reasoning
- Overall persuasiveness

Respond in JSON format:
{{
  "winner": "Participant Name",
  "verdict": "Your comprehensive verdict here..."
}}"""

        # Summarize all rounds
        debate_summary = f"**Complete Debate Summary ({len(all_rounds)} rounds)**\n\n"

        for round_data in all_rounds:
            debate_summary += f"**Round {round_data.round_number}**\n"
            for response in round_data.responses:
                debate_summary += f"- **{response.participant_name}**: {response.content[:200]}...\n"

            if round_data.judge_assessment:
                scores = round_data.judge_assessment.participant_scores
                debate_summary += f"  Scores: {scores}\n"
            debate_summary += "\n"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": debate_summary}
        ]

        return messages

    def _format_rubric(self) -> str:
        """Format rubric dimensions for prompt"""
        lines = []
        for dimension, description in self.RUBRIC_DIMENSIONS.items():
            lines.append(f"- {dimension.title()}: {description}")
        return "\n".join(lines)

    def _parse_judge_response(self, response: str) -> Dict:
        """Parse judge's JSON response"""
        try:
            # Try to extract JSON from response
            start = response.find("{")
            end = response.rfind("}") + 1
            json_str = response[start:end]
            data = json.loads(json_str)

            # Validate structure
            assert "rubric_scores" in data
            assert "participant_scores" in data
            assert "analysis" in data

            return data

        except Exception as e:
            logger.error(f"Error parsing judge response: {e}")
            # Return default structure
            return {
                "rubric_scores": {dim: 5.0 for dim in self.RUBRIC_DIMENSIONS},
                "participant_scores": {},
                "analysis": "Error parsing judge assessment. Default scores assigned."
            }

    def _parse_verdict_response(self, response: str) -> Dict:
        """Parse final verdict JSON response"""
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            json_str = response[start:end]
            data = json.loads(json_str)

            assert "winner" in data
            assert "verdict" in data

            return data

        except Exception as e:
            logger.error(f"Error parsing verdict response: {e}")
            return {
                "winner": "No winner",
                "verdict": f"Error parsing verdict: {str(e)}"
            }

    def _check_stopping_criteria(
        self,
        config: DebateConfig,
        round_data: DebateRound,
        all_rounds: List[DebateRound],
        assessment_data: Dict
    ) -> Tuple[bool, str]:
        """
        Check if debate should continue

        Returns:
            Tuple of (should_continue, stopping_reason)
        """
        # Check max rounds
        if config.max_rounds and round_data.round_number >= config.max_rounds:
            return False, f"Maximum rounds ({config.max_rounds}) reached"

        # Check for diminishing returns (low novelty scores)
        if round_data.round_number >= 3:
            novelty_score = assessment_data["rubric_scores"].get("novelty", 10.0)
            if novelty_score < 3.0:
                return False, "Diminishing returns detected (low novelty score)"

        # Check for repetition across recent rounds
        if len(all_rounds) >= 3:
            if self._detect_repetition(all_rounds[-3:]):
                return False, "Repetitive arguments detected"

        # Check for convergence (similar scores)
        participant_scores = assessment_data["participant_scores"]
        if len(participant_scores) >= 2:
            scores = list(participant_scores.values())
            score_range = max(scores) - min(scores)
            if round_data.round_number >= 5 and score_range < 0.5:
                return False, "Debate has reached convergence (similar performance)"

        # Continue by default
        return True, ""

    def _detect_repetition(self, recent_rounds: List[DebateRound]) -> bool:
        """
        Detect if arguments are becoming repetitive

        Simple heuristic: check if novelty scores are consistently low
        """
        if not recent_rounds:
            return False

        novelty_scores = []
        for round_data in recent_rounds:
            if round_data.judge_assessment:
                score = round_data.judge_assessment.rubric_scores.get("novelty", 10.0)
                novelty_scores.append(score)

        if not novelty_scores:
            return False

        avg_novelty = sum(novelty_scores) / len(novelty_scores)
        return avg_novelty < 4.0  # Threshold for repetition

    def _create_default_assessment(self, round_data: DebateRound, error: str) -> JudgeAssessment:
        """Create default assessment on error"""
        return JudgeAssessment(
            round_number=round_data.round_number,
            rubric_scores={dim: 5.0 for dim in self.RUBRIC_DIMENSIONS},
            participant_scores={
                response.participant_name: 5.0
                for response in round_data.responses
            },
            analysis=f"Error during assessment: {error}. Default scores assigned.",
            should_continue=True,
            stopping_reason=None
        )


# Singleton instance
judge_service = JudgeService()
