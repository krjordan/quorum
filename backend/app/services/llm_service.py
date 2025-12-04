import asyncio
from typing import AsyncGenerator, List, Dict, Any, Optional
import litellm
from litellm import acompletion
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
