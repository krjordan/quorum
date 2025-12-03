"""
Token Counter - Utilities for counting tokens and estimating costs
"""
import tiktoken
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class TokenCounter:
    """Token counting and cost estimation utilities"""

    # Token pricing per 1M tokens (as of 2024)
    PRICING = {
        # OpenAI
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
        "gpt-4": {"input": 30.00, "output": 60.00},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},

        # Anthropic
        "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
        "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
        "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
        "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
        "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},

        # Google
        "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
        "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
        "gemini-pro": {"input": 0.50, "output": 1.50},

        # Mistral
        "mistral-large-latest": {"input": 2.00, "output": 6.00},
        "mistral-medium-latest": {"input": 2.70, "output": 8.10},
        "mistral-small-latest": {"input": 0.20, "output": 0.60},
        "open-mistral-7b": {"input": 0.25, "output": 0.25},
    }

    def __init__(self):
        self.encoders: Dict[str, tiktoken.Encoding] = {}

    def _get_encoder(self, model: str) -> tiktoken.Encoding:
        """Get or create tiktoken encoder for model"""
        if model not in self.encoders:
            try:
                # Try to get model-specific encoding
                if "gpt-4" in model.lower():
                    self.encoders[model] = tiktoken.encoding_for_model("gpt-4")
                elif "gpt-3.5" in model.lower():
                    self.encoders[model] = tiktoken.encoding_for_model("gpt-3.5-turbo")
                else:
                    # Default to cl100k_base (used by GPT-4, Claude, etc.)
                    self.encoders[model] = tiktoken.get_encoding("cl100k_base")
            except Exception as e:
                logger.warning(f"Could not get encoder for {model}, using cl100k_base: {e}")
                self.encoders[model] = tiktoken.get_encoding("cl100k_base")

        return self.encoders[model]

    def count_tokens(self, text: str, model: str) -> int:
        """
        Count tokens in text for given model

        Args:
            text: Text to count tokens for
            model: Model identifier

        Returns:
            Token count
        """
        try:
            encoder = self._get_encoder(model)
            return len(encoder.encode(text))
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            # Fallback: rough estimate (1 token ≈ 4 characters)
            return len(text) // 4

    def count_message_tokens(self, messages: List[Dict[str, str]], model: str) -> int:
        """
        Count tokens in message list (includes formatting overhead)

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier

        Returns:
            Total token count including message formatting
        """
        try:
            encoder = self._get_encoder(model)
            num_tokens = 0

            for message in messages:
                # Every message follows <im_start>{role/name}\n{content}<im_end>\n
                num_tokens += 4  # Message formatting overhead
                for key, value in message.items():
                    num_tokens += len(encoder.encode(str(value)))

            num_tokens += 2  # Every reply is primed with <im_start>assistant
            return num_tokens

        except Exception as e:
            logger.error(f"Error counting message tokens: {e}")
            # Fallback: sum individual texts + overhead
            total = sum(self.count_tokens(msg.get("content", ""), model) for msg in messages)
            return total + len(messages) * 4

    def estimate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """
        Estimate cost for token usage

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model identifier

        Returns:
            Estimated cost in USD
        """
        # Normalize model name
        model_lower = model.lower()

        # Find matching pricing
        pricing = None
        for model_key, model_pricing in self.PRICING.items():
            if model_key.lower() in model_lower:
                pricing = model_pricing
                break

        if not pricing:
            logger.warning(f"No pricing data for {model}, using GPT-4o as default")
            pricing = self.PRICING["gpt-4o"]

        # Calculate cost (pricing is per 1M tokens)
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def get_model_pricing(self, model: str) -> Dict[str, float]:
        """
        Get pricing information for model

        Args:
            model: Model identifier

        Returns:
            Dict with 'input' and 'output' pricing per 1M tokens
        """
        model_lower = model.lower()

        for model_key, pricing in self.PRICING.items():
            if model_key.lower() in model_lower:
                return pricing

        # Default to GPT-4o pricing
        return self.PRICING["gpt-4o"]

    def format_cost(self, cost: float) -> str:
        """Format cost as currency string"""
        return f"${cost:.4f}"

    def get_cost_warning_level(self, cost: float, threshold: float) -> str:
        """
        Get warning level based on cost threshold

        Args:
            cost: Current cost in USD
            threshold: Warning threshold in USD

        Returns:
            Warning level: 'none', 'low', 'medium', 'high', 'critical'
        """
        if cost < threshold * 0.5:
            return "none"
        elif cost < threshold * 0.75:
            return "low"
        elif cost < threshold:
            return "medium"
        elif cost < threshold * 1.5:
            return "high"
        else:
            return "critical"


# Singleton instance
token_counter = TokenCounter()
