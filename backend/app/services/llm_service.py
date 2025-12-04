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

    async def stream_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        model_to_use = model or self.default_model
        print(f"[LLM Service] Starting stream for model: {model_to_use}")

        # Use Anthropic SDK directly for Claude models (LiteLLM streaming is broken)
        if "claude" in model_to_use.lower() or "anthropic" in model_to_use.lower():
            print(f"[LLM Service] Using native Anthropic SDK for {model_to_use}")
            async for chunk in self._stream_anthropic(messages, model_to_use):
                yield chunk
            return

        # Use LiteLLM for other models (OpenAI, Gemini, etc.)
        try:
            response = await acompletion(
                model=model_to_use,
                messages=messages,
                stream=True,
                api_key=self._get_api_key(model_to_use),
            )

            chunk_count = 0
            async for chunk in response:
                chunk_count += 1
                if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        yield delta.content

            print(f"[LLM Service] Stream complete. Total chunks: {chunk_count}")

        except Exception as e:
            print(f"LLM streaming error: {str(e)}")
            raise

    async def _stream_anthropic(
        self,
        messages: List[Dict[str, str]],
        model: str
    ) -> AsyncGenerator[str, None]:
        """Stream completion using Anthropic SDK directly"""
        try:
            # Extract system message if present
            system_message = None
            user_messages = []

            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    user_messages.append(msg)

            # Initialize Anthropic client
            client = AsyncAnthropic(api_key=settings.anthropic_api_key)

            # Create streaming request
            kwargs = {
                "model": model,
                "messages": user_messages,
                "max_tokens": 4096,
                "stream": True,
            }

            if system_message:
                kwargs["system"] = system_message

            print(f"[Anthropic SDK] Starting stream with {len(user_messages)} messages")

            chunk_count = 0
            async with client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    chunk_count += 1
                    if text:
                        yield text

            print(f"[Anthropic SDK] Stream complete. Total chunks: {chunk_count}")

        except Exception as e:
            print(f"Anthropic streaming error: {str(e)}")
            raise

    async def get_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
    ) -> str:
        model_to_use = model or self.default_model

        try:
            response = await acompletion(
                model=model_to_use,
                messages=messages,
                stream=False,
                api_key=self._get_api_key(model_to_use),
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"LLM completion error: {str(e)}")
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
