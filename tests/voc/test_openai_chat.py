import asyncio

import pytest

from allstar.shared.bedrock import BedrockIncompleteResponseError
from allstar.voc.llm.openai_chat import OpenAIChat
from allstar.voc.runtime.llm_retry import LLMRetryError


class TokenLimitedClient:
    def __init__(self):
        self.limits = []

    async def generate_async(self, _prompt, *, max_tokens, **_kwargs):
        self.limits.append(max_tokens)
        if len(self.limits) == 1:
            raise BedrockIncompleteResponseError(
                "출력 한도 소진",
                status="incomplete",
                reason="max_output_tokens",
            )
        return '{"task":"both"}'


def test_output_limit_is_expanded_once_only_after_token_exhaustion():
    chat = OpenAIChat(model="openai.gpt-oss-20b", max_attempts=1)
    chat.client = TokenLimitedClient()

    result = asyncio.run(chat("질문", max_tokens=900))

    assert result == '{"task":"both"}'
    assert chat.client.limits == [900, 1800]


def test_non_token_incomplete_response_is_not_expanded():
    class FilteredClient:
        def __init__(self):
            self.limits = []

        async def generate_async(self, _prompt, *, max_tokens, **_kwargs):
            self.limits.append(max_tokens)
            raise BedrockIncompleteResponseError(
                "콘텐츠 필터",
                status="incomplete",
                reason="content_filter",
            )

    chat = OpenAIChat(model="openai.gpt-oss-20b", max_attempts=1)
    chat.client = FilteredClient()

    with pytest.raises(LLMRetryError):
        asyncio.run(chat("질문", max_tokens=900))

    assert chat.client.limits == [900]
