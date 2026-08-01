"""Amazon Bedrock을 통한 GPT·Claude 호출의 공통 구현.

GPT는 Bedrock Mantle Responses API를 SigV4로 직접 호출하고, Claude는
Bedrock Runtime의 네이티브 Anthropic 요청 형식을 사용한다. 두 경로 모두
EC2 인스턴스 프로필을 포함한 boto3 기본 자격 증명 체인을 사용하므로
애플리케이션 전용 장기 API 키를 저장하지 않는다.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import boto3
import httpx
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.config import Config


DEFAULT_MANTLE_REGION = "us-west-2"
DEFAULT_RUNTIME_REGION = "ap-northeast-2"
MANTLE_SERVICE = "bedrock-mantle"
logger = logging.getLogger(__name__)


class BedrockConfigurationError(RuntimeError):
    """AWS 자격 증명이나 모델 설정이 없어 호출을 시작할 수 없을 때 발생한다."""


class BedrockResponseError(RuntimeError):
    """Bedrock 응답에서 텍스트를 찾지 못했을 때 발생한다."""

    def __init__(
        self,
        message: str,
        *,
        status: str | None = None,
        reason: str | None = None,
    ) -> None:
        self.status = status
        self.reason = reason
        super().__init__(message)


class BedrockIncompleteResponseError(BedrockResponseError):
    """Responses API가 완료되지 않은 상태로 종료되었을 때 발생한다."""


def mantle_region() -> str:
    return os.getenv("BEDROCK_MANTLE_REGION", DEFAULT_MANTLE_REGION)


def runtime_region() -> str:
    return os.getenv(
        "BEDROCK_RUNTIME_REGION",
        os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", DEFAULT_RUNTIME_REGION)),
    )


def normalize_gpt_model(model: str) -> str:
    value = model.strip()
    return value if value.startswith("openai.") else f"openai.{value}"


def normalize_claude_model(model: str) -> str:
    value = model.strip()
    if value.startswith(("global.anthropic.", "anthropic.")):
        return value
    return f"global.anthropic.{value}"


def _credentials():
    credentials = boto3.Session().get_credentials()
    if credentials is None:
        raise BedrockConfigurationError(
            "AWS 자격 증명을 찾지 못했습니다. EC2 IAM 역할 또는 AWS 기본 자격 증명 체인을 설정하세요."
        )
    return credentials.get_frozen_credentials()


def _signed_headers(url: str, body: bytes, region: str) -> dict[str, str]:
    request = AWSRequest(
        method="POST",
        url=url,
        data=body,
        headers={
            "content-type": "application/json",
            "host": urlparse(url).netloc,
        },
    )
    SigV4Auth(_credentials(), MANTLE_SERVICE, region).add_auth(request)
    return {str(key): str(value) for key, value in request.headers.items()}


def _extract_mantle_text(payload: dict[str, Any]) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct

    parts: list[str] = []
    for output in payload.get("output", []):
        if not isinstance(output, dict):
            continue
        for content in output.get("content", []):
            if not isinstance(content, dict):
                continue
            if content.get("type") not in {None, "output_text"}:
                continue
            text = content.get("text")
            if isinstance(text, str) and text:
                parts.append(text)
    if parts:
        return "\n".join(parts)

    status = str(payload.get("status") or "unknown")
    incomplete_details = payload.get("incomplete_details")
    reason = None
    if isinstance(incomplete_details, dict):
        reason_value = incomplete_details.get("reason")
        if reason_value:
            reason = str(reason_value)

    output_types: list[str] = []
    content_types: list[str] = []
    for output in payload.get("output", []):
        if not isinstance(output, dict):
            continue
        output_types.append(str(output.get("type") or "unknown"))
        for content in output.get("content", []):
            if isinstance(content, dict):
                content_types.append(str(content.get("type") or "unknown"))

    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    output_details = (
        usage.get("output_tokens_details")
        if isinstance(usage.get("output_tokens_details"), dict)
        else {}
    )
    logger.warning(
        "Bedrock Mantle 텍스트 출력 없음: status=%s reason=%s "
        "output_types=%s content_types=%s input_tokens=%s output_tokens=%s reasoning_tokens=%s",
        status,
        reason or "none",
        output_types,
        content_types,
        usage.get("input_tokens"),
        usage.get("output_tokens"),
        output_details.get("reasoning_tokens"),
    )

    if status == "incomplete":
        detail = reason or "unknown"
        raise BedrockIncompleteResponseError(
            f"Bedrock Mantle 응답이 완료되지 않았습니다. reason={detail}",
            status=status,
            reason=reason,
        )
    raise BedrockResponseError(
        f"Bedrock Mantle 응답에서 출력 텍스트를 찾지 못했습니다. status={status}",
        status=status,
        reason=reason,
    )


@dataclass
class BedrockGPT:
    model: str
    region: str = ""
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        self.model = normalize_gpt_model(self.model)
        self.region = self.region or mantle_region()

    @property
    def endpoint(self) -> str:
        path = "openai/v1/responses" if self.model.startswith("openai.gpt-5.") else "v1/responses"
        return f"https://bedrock-mantle.{self.region}.api.aws/{path}"

    def _payload(
        self,
        prompt: str | list[dict[str, str]],
        max_tokens: int,
        reasoning: str | None,
        verbosity: str | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "input": prompt,
            "max_output_tokens": max_tokens,
            "store": False,
        }
        if reasoning and reasoning != "none":
            payload["reasoning"] = {"effort": reasoning}
        if verbosity:
            payload["text"] = {"verbosity": verbosity}
        return payload

    def generate(
        self,
        prompt: str | list[dict[str, str]],
        *,
        max_tokens: int = 900,
        reasoning: str | None = None,
        verbosity: str | None = "low",
    ) -> str:
        payload = self._payload(prompt, max_tokens, reasoning, verbosity)
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        response = httpx.post(
            self.endpoint,
            content=body,
            headers=_signed_headers(self.endpoint, body, self.region),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return _extract_mantle_text(response.json()).strip()

    async def generate_async(
        self,
        prompt: str | list[dict[str, str]],
        *,
        max_tokens: int = 900,
        reasoning: str | None = None,
        verbosity: str | None = "low",
    ) -> str:
        payload = self._payload(prompt, max_tokens, reasoning, verbosity)
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                self.endpoint,
                content=body,
                headers=_signed_headers(self.endpoint, body, self.region),
            )
        response.raise_for_status()
        return _extract_mantle_text(response.json()).strip()


@dataclass
class BedrockClaude:
    model: str
    region: str = ""
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        self.model = normalize_claude_model(self.model)
        self.region = self.region or runtime_region()

    def _payload(
        self,
        prompt: str,
        max_tokens: int,
        effort: str | None,
        thinking: str | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if effort in {"low", "medium", "high", "max"}:
            payload["output_config"] = {"effort": effort}
        if thinking == "disabled":
            payload["thinking"] = {"type": "disabled"}
        return payload

    def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 1024,
        effort: str | None = "low",
        thinking: str | None = "disabled",
    ) -> str:
        client = boto3.client(
            "bedrock-runtime",
            region_name=self.region,
            config=Config(
                connect_timeout=self.timeout_seconds,
                read_timeout=self.timeout_seconds,
                retries={"max_attempts": 0},
            ),
        )
        response = client.invoke_model(
            modelId=self.model,
            body=json.dumps(self._payload(prompt, max_tokens, effort, thinking)),
            contentType="application/json",
            accept="application/json",
        )
        payload = json.loads(response["body"].read())
        parts = [
            block["text"]
            for block in payload.get("content", [])
            if isinstance(block, dict) and isinstance(block.get("text"), str)
        ]
        if not parts:
            raise BedrockResponseError("Bedrock Runtime 응답에서 Claude 텍스트를 찾지 못했습니다.")
        return "\n".join(parts).strip()

    async def generate_async(
        self,
        prompt: str,
        *,
        max_tokens: int = 1024,
        effort: str | None = "low",
        thinking: str | None = "disabled",
    ) -> str:
        import asyncio

        return await asyncio.to_thread(
            self.generate,
            prompt,
            max_tokens=max_tokens,
            effort=effort,
            thinking=thinking,
        )
