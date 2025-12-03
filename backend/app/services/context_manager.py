"""
Context Manager - Manages conversation context with sliding window and token tracking
"""
from typing import List, Dict, Tuple
import logging
from app.models.debate import DebateConfig, DebateRound, ParticipantConfig
from app.utils.token_counter import token_counter

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages debate context with sliding window and token limits"""

    def __init__(self):
        self.max_context_tokens = 100_000  # Conservative limit

    def build_context(
        self,
        config: DebateConfig,
        rounds: List[DebateRound],
        participant: ParticipantConfig
    ) -> Tuple[List[Dict[str, str]], int]:
        """
        Build context for a participant with sliding window

        Args:
            config: Debate configuration
            rounds: All debate rounds
            participant: Participant to build context for

        Returns:
            Tuple of (messages, token_count)
        """
        messages = []

        # System prompt
        system_prompt = self._build_system_prompt(config, participant)
        messages.append({"role": "system", "content": system_prompt})

        # Apply sliding window to rounds
        window_size = config.context_window_rounds
        relevant_rounds = rounds[-window_size:] if len(rounds) > window_size else rounds

        # Build conversation history
        for round_data in relevant_rounds:
            for response in round_data.responses:
                # Add each participant's response
                messages.append({
                    "role": "assistant" if response.participant_name == participant.persona.name else "user",
                    "content": f"**{response.participant_name}**: {response.content}"
                })

            # Add judge assessment if available
            if round_data.judge_assessment:
                assessment = round_data.judge_assessment
                judge_summary = f"**Judge Assessment (Round {assessment.round_number})**: {assessment.analysis}"
                messages.append({"role": "system", "content": judge_summary})

        # Add current round prompt
        current_round = len(rounds) + 1
        round_prompt = self._build_round_prompt(config, current_round, participant)
        messages.append({"role": "user", "content": round_prompt})

        # Count tokens
        token_count = token_counter.count_message_tokens(messages, participant.model)

        # Truncate if necessary
        if token_count > self.max_context_tokens:
            messages, token_count = self._truncate_context(messages, participant.model)

        logger.info(f"Built context for {participant.persona.name}: {len(messages)} messages, {token_count} tokens")

        return messages, token_count

    def _build_system_prompt(self, config: DebateConfig, participant: ParticipantConfig) -> str:
        """Build system prompt for participant"""
        base_prompt = f"""You are participating in a structured debate on the topic: "{config.topic}"

Your Role: {participant.persona.name}
Your Perspective: {participant.persona.role}

Debate Format: {config.format.value}
Number of Participants: {len(config.participants)}

Guidelines:
1. Stay in character and argue from your assigned perspective
2. Engage directly with other participants' arguments
3. Provide clear reasoning and evidence when possible
4. Be respectful but assertive in your arguments
5. Build on previous points and address counterarguments
6. Aim for substantive contributions that advance the debate

Your responses should be concise (200-400 words) and focused."""

        if participant.persona.system_prompt:
            base_prompt += f"\n\nAdditional Instructions: {participant.persona.system_prompt}"

        return base_prompt

    def _build_round_prompt(self, config: DebateConfig, round_number: int, participant: ParticipantConfig) -> str:
        """Build prompt for current round"""
        if round_number == 1:
            return f"This is Round {round_number}. Present your opening argument on the topic: '{config.topic}'"
        else:
            return f"This is Round {round_number}. Respond to the previous arguments and continue the debate."

    def _truncate_context(self, messages: List[Dict[str, str]], model: str) -> Tuple[List[Dict[str, str]], int]:
        """
        Truncate context to fit within token limits

        Strategy:
        1. Keep system prompt (first message)
        2. Keep current round prompt (last message)
        3. Remove oldest conversation messages until under limit
        """
        logger.warning(f"Context exceeds {self.max_context_tokens} tokens, truncating...")

        if len(messages) <= 2:
            # Can't truncate further (system + user prompt)
            token_count = token_counter.count_message_tokens(messages, model)
            return messages, token_count

        # Keep first (system) and last (current prompt)
        system_msg = messages[0]
        current_prompt = messages[-1]
        middle_messages = messages[1:-1]

        # Remove oldest messages until under limit
        while middle_messages:
            truncated = [system_msg] + middle_messages + [current_prompt]
            token_count = token_counter.count_message_tokens(truncated, model)

            if token_count <= self.max_context_tokens:
                logger.info(f"Truncated to {len(truncated)} messages, {token_count} tokens")
                return truncated, token_count

            # Remove oldest middle message
            middle_messages.pop(0)

        # Worst case: just system and current prompt
        final_messages = [system_msg, current_prompt]
        token_count = token_counter.count_message_tokens(final_messages, model)
        logger.warning(f"Heavy truncation: {len(final_messages)} messages, {token_count} tokens")

        return final_messages, token_count

    def estimate_response_cost(
        self,
        context_tokens: int,
        estimated_response_tokens: int,
        model: str
    ) -> float:
        """
        Estimate cost for a response

        Args:
            context_tokens: Tokens in context (input)
            estimated_response_tokens: Estimated response length
            model: Model identifier

        Returns:
            Estimated cost in USD
        """
        return token_counter.estimate_cost(
            input_tokens=context_tokens,
            output_tokens=estimated_response_tokens,
            model=model
        )

    def check_cost_warning(self, total_cost: float, threshold: float) -> Dict[str, any]:
        """
        Check if cost warning should be issued

        Args:
            total_cost: Current total cost
            threshold: Warning threshold

        Returns:
            Dict with warning info
        """
        warning_level = token_counter.get_cost_warning_level(total_cost, threshold)

        return {
            "should_warn": warning_level in ["medium", "high", "critical"],
            "level": warning_level,
            "current_cost": total_cost,
            "threshold": threshold,
            "percentage": (total_cost / threshold * 100) if threshold > 0 else 0,
            "message": self._get_warning_message(warning_level, total_cost, threshold)
        }

    def _get_warning_message(self, level: str, cost: float, threshold: float) -> str:
        """Get appropriate warning message for cost level"""
        if level == "none":
            return ""
        elif level == "low":
            return f"Debate cost approaching threshold ({token_counter.format_cost(cost)} / {token_counter.format_cost(threshold)})"
        elif level == "medium":
            return f"⚠️ Debate cost near threshold ({token_counter.format_cost(cost)} / {token_counter.format_cost(threshold)})"
        elif level == "high":
            return f"⚠️ Debate cost exceeded threshold ({token_counter.format_cost(cost)} / {token_counter.format_cost(threshold)})"
        else:  # critical
            return f"🚨 CRITICAL: Debate cost significantly exceeded threshold ({token_counter.format_cost(cost)} / {token_counter.format_cost(threshold)})"


# Singleton instance
context_manager = ContextManager()
