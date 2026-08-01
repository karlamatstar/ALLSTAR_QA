"""Bedrock Mantle에서 GPT를 호출하는 비동기 래퍼."""

from __future__ import annotations

import logging
import os

from allstar.shared.bedrock import BedrockGPT, BedrockIncompleteResponseError
from allstar.voc.runtime.env_loader import load_env
from allstar.voc.runtime.llm_retry import LLMRetryError, call_with_retry

load_env()
logger = logging.getLogger(__name__)


class OpenAIChat:
    def __init__(
        self,
        model: str | None = None,
        max_attempts: int | None = None,
        reasoning_effort: str | None = None,
        verbosity: str | None = None,
    ):
        self.model = model or os.environ.get("OPENAI_MODEL", "openai.gpt-oss-20b")
        self.max_attempts = max_attempts or int(os.environ.get("LLM_MAX_ATTEMPTS", "3"))
        self.reasoning_effort = reasoning_effort or os.environ.get("OPENAI_REASONING_EFFORT", "none")
        self.verbosity = verbosity or os.environ.get("OPENAI_VERBOSITY", "low")
        self.client = BedrockGPT(
            model=self.model,
            timeout_seconds=float(os.environ.get("LLM_TIMEOUT_SECONDS", "30")),
        )

    async def __call__(self, prompt: str, max_tokens: int | None = None) -> str:
        output_limit = max_tokens or int(os.environ.get("OPENAI_MAX_COMPLETION_TOKENS", "900"))

        async def request(limit: int):
            return await self.client.generate_async(
                prompt,
                reasoning=self.reasoning_effort,
                verbosity=self.verbosity,
                max_tokens=limit,
            )

        try:
            response, _attempts = await call_with_retry(
                "Bedrock Mantle GPT",
                lambda: request(output_limit),
                max_attempts=self.max_attempts,
            )
        except LLMRetryError as error:
            cause = error.last_error
            if not (
                isinstance(cause, BedrockIncompleteResponseError)
                and cause.reason in {"max_output_tokens", "max_tokens"}
            ):
                raise
            expanded_limit = max(output_limit * 2, 1800)
            logger.warning(
                "Bedrock Mantle 출력 한도 소진으로 1회 확대 재시도: model=%s before=%s after=%s",
                self.model,
                output_limit,
                expanded_limit,
            )
            response, _attempts = await call_with_retry(
                "Bedrock Mantle GPT",
                lambda: request(expanded_limit),
                max_attempts=self.max_attempts,
            )
        return response
