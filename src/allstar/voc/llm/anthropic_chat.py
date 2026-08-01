"""Bedrock Runtime에서 Claude를 호출하고 GPT로 대체할 수 있는 래퍼."""

from __future__ import annotations

import os

from allstar.shared.bedrock import BedrockClaude
from allstar.voc.runtime.env_loader import load_env
from allstar.voc.runtime.llm_retry import (
    AllProvidersFailedError,
    LLMRetryError,
    call_with_retry,
    failure_from,
)

load_env()


class AnthropicChat:
    def __init__(
        self,
        model: str | None = None,
        fallback_to_openai: bool | None = None,
        effort: str | None = None,
        thinking: str | None = None,
        max_attempts: int | None = None,
    ):
        self.model = model or os.environ.get(
            "A2A_MODEL_POLICY", "global.anthropic.claude-haiku-4-5-20251001-v1:0"
        )
        if fallback_to_openai is None:
            fallback_to_openai = os.environ.get("LLM_ALLOW_FALLBACK", "true").lower() == "true"
        self.fallback_to_openai = fallback_to_openai
        self.max_attempts = max_attempts or int(os.environ.get("LLM_MAX_ATTEMPTS", "3"))
        self.effort = (effort or os.environ.get("ANTHROPIC_EFFORT_POLICY", "none")).lower()
        self.thinking = (thinking or os.environ.get("ANTHROPIC_THINKING_POLICY", "disabled")).lower()
        self.client = BedrockClaude(
            model=self.model,
            timeout_seconds=float(os.environ.get("LLM_TIMEOUT_SECONDS", "30")),
        )

    async def __call__(self, prompt: str, max_tokens: int = 1024) -> str:
        async def request():
            return await self.client.generate_async(
                prompt,
                max_tokens=max_tokens,
                effort=self.effort,
                thinking=self.thinking,
            )

        try:
            response, _attempts = await call_with_retry(
                "Bedrock Runtime Claude", request, max_attempts=self.max_attempts
            )
        except LLMRetryError as anthropic_error:
            if not self.fallback_to_openai:
                raise
            print(f"[AnthropicChat] {anthropic_error}. OpenAI 대체 호출을 시도합니다.")
            try:
                from allstar.voc.llm.openai_chat import OpenAIChat
                return await OpenAIChat(max_attempts=self.max_attempts)(prompt)
            except LLMRetryError as openai_error:
                raise AllProvidersFailedError([
                    failure_from(anthropic_error),
                    failure_from(openai_error),
                ]) from openai_error

        return response
