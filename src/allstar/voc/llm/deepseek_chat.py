"""Bedrock Mantle에서 DeepSeek Chat Completions를 호출하는 비동기 래퍼."""

from __future__ import annotations

import os

from allstar.shared.bedrock import BedrockChatCompletions
from allstar.voc.runtime.env_loader import load_env
from allstar.voc.runtime.llm_retry import call_with_retry

load_env()


class DeepSeekChat:
    def __init__(self, model: str | None = None, max_attempts: int | None = None):
        self.model = model or os.environ.get("DEEPSEEK_MODEL", "deepseek.v3.1")
        self.max_attempts = max_attempts or int(os.environ.get("LLM_MAX_ATTEMPTS", "3"))
        self.client = BedrockChatCompletions(
            model=self.model,
            provider="deepseek",
            timeout_seconds=float(os.environ.get("LLM_TIMEOUT_SECONDS", "30")),
        )

    async def __call__(self, prompt: str, max_tokens: int | None = None) -> str:
        output_limit = max_tokens or int(
            os.environ.get("DEEPSEEK_MAX_COMPLETION_TOKENS", "900")
        )

        async def request():
            return await self.client.generate_async(prompt, max_tokens=output_limit)

        response, _attempts = await call_with_retry(
            "Bedrock Mantle DeepSeek", request, max_attempts=self.max_attempts
        )
        return response
