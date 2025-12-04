import asyncio
from typing import AsyncGenerator, List, Dict, Any, Optional
import litellm
from litellm import acompletion
from anthropic import AsyncAnthropic
from app.config.settings import settings

# Configure LiteLLM
litellm.set_verbose = settings.debug
litellm.telemetry = settings.litellm_telemetry


class LLMService:
    def __init__(self):
        self.default_model = "gpt-4o"
        self.anthropic_client = None

    async def stream_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        model_to_use = model or self.default_model

        try:
            response = await acompletion(
                model=model_to_use,
                messages=messages,
                stream=True,
                api_key=self._get_api_key(model_to_use),
            )

            async for chunk in response:
                if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        yield delta.content

        except Exception as e:
            print(f"LLM streaming error: {str(e)}")
            raise

    async def get_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
    ) -> str:
        model_to_use = model or self.default_model

        # Use Anthropic SDK directly for Claude models (LiteLLM is broken)
        if "claude" in model_to_use.lower():
            return await self._get_claude_completion(messages, model_to_use)

        # Use LiteLLM for other models
        try:
            response = await acompletion(
                model=model_to_use,
                messages=messages,
                stream=False,
                api_key=self._get_api_key(model_to_use),
            )

            if hasattr(response, 'choices') and len(response.choices) > 0:
                content = response.choices[0].message.content
                if content is None:
                    raise ValueError(f"LiteLLM returned None content for model {model_to_use}")
                return content
            else:
                raise ValueError(f"No choices in response for model {model_to_use}")

        except Exception as e:
            print(f"LLM completion error: {str(e)}")
            raise

    async def _get_claude_completion(
        self,
        messages: List[Dict[str, str]],
        model: str
    ) -> str:
        """Get completion using Anthropic SDK directly (LiteLLM broken for Claude)"""
        try:
            # Initialize client if needed
            if self.anthropic_client is None:
                self.anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)

            # Extract system message
            system_message = None
            user_messages = []

            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    user_messages.append(msg)

            # Create request
            kwargs = {
                "model": model,
                "messages": user_messages,
                "max_tokens": 4096,
            }

            if system_message:
                kwargs["system"] = system_message

            print(f"[Anthropic SDK] Getting completion for {model}")
            response = await self.anthropic_client.messages.create(**kwargs)

            # Extract text content
            content = response.content[0].text
            print(f"[Anthropic SDK] Got {len(content)} characters")

            return content

        except Exception as e:
            print(f"Anthropic SDK error: {str(e)}")
            raise

    def _get_api_key(self, model: str) -> str:
        model_lower = model.lower()

        if "gpt" in model_lower or "openai" in model_lower:
            return settings.openai_api_key
        elif "claude" in model_lower or "anthropic" in model_lower:
            return settings.anthropic_api_key
        elif "gemini" in model_lower or "google" in model_lower:
            return settings.google_api_key
        elif "mistral" in model_lower:
            return settings.mistral_api_key
        else:
            return settings.openai_api_key


llm_service = LLMService()
