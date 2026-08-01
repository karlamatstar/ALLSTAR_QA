import io
import json

import pytest

from allstar.shared import bedrock


def test_model_ids_are_normalized_for_each_bedrock_surface():
    assert bedrock.normalize_gpt_model("gpt-oss-20b") == "openai.gpt-oss-20b"
    assert bedrock.normalize_gpt_model("openai.gpt-oss-120b") == "openai.gpt-oss-120b"
    assert (
        bedrock.normalize_claude_model("claude-haiku-4-5-20251001-v1:0")
        == "global.anthropic.claude-haiku-4-5-20251001-v1:0"
    )


def test_gpt_uses_signed_mantle_responses_endpoint(monkeypatch):
    captured = {}

    class FakeResponse:
        @staticmethod
        def raise_for_status():
            return None

        @staticmethod
        def json():
            return {
                "output": [
                    {"content": [{"type": "reasoning_text", "text": "내부 추론"}]},
                    {"content": [{"type": "output_text", "text": "응답"}]},
                ]
            }

    def fake_post(url, *, content, headers, timeout):
        captured.update(url=url, content=content, headers=headers, timeout=timeout)
        return FakeResponse()

    monkeypatch.setattr(bedrock, "_signed_headers", lambda *_args: {"Authorization": "signed"})
    monkeypatch.setattr(bedrock.httpx, "post", fake_post)

    result = bedrock.BedrockGPT("gpt-oss-20b", region="us-west-2").generate(
        "질문", max_tokens=123, reasoning="none"
    )

    payload = json.loads(captured["content"])
    assert captured["url"] == "https://bedrock-mantle.us-west-2.api.aws/v1/responses"
    assert captured["headers"]["Authorization"] == "signed"
    assert payload["model"] == "openai.gpt-oss-20b"
    assert payload["store"] is False
    assert "reasoning" not in payload
    assert result == "응답"


def test_gpt_5_models_use_their_dedicated_openai_path():
    client = bedrock.BedrockGPT("openai.gpt-5.6-luna", region="us-west-2")
    assert client.endpoint == "https://bedrock-mantle.us-west-2.api.aws/openai/v1/responses"


def test_mantle_incomplete_response_preserves_safe_diagnostics(caplog):
    payload = {
        "status": "incomplete",
        "incomplete_details": {"reason": "max_output_tokens"},
        "input": "로그에 남으면 안 되는 사용자 질문",
        "output": [{"type": "reasoning", "content": []}],
        "usage": {
            "input_tokens": 120,
            "output_tokens": 900,
            "output_tokens_details": {"reasoning_tokens": 900},
        },
    }

    with pytest.raises(bedrock.BedrockIncompleteResponseError) as caught:
        bedrock._extract_mantle_text(payload)

    assert caught.value.status == "incomplete"
    assert caught.value.reason == "max_output_tokens"
    assert "status=incomplete" in caplog.text
    assert "reason=max_output_tokens" in caplog.text
    assert "사용자 질문" not in caplog.text


def test_mantle_completed_response_without_text_reports_status():
    with pytest.raises(bedrock.BedrockResponseError) as caught:
        bedrock._extract_mantle_text({"status": "completed", "output": []})

    assert not isinstance(caught.value, bedrock.BedrockIncompleteResponseError)
    assert caught.value.status == "completed"
    assert caught.value.reason is None


def test_reasoning_only_completed_response_at_requested_limit_is_token_exhaustion():
    payload = {
        "status": "completed",
        "output": [
            {"type": "reasoning", "content": [{"type": "reasoning_text", "text": "추론"}]}
        ],
        "usage": {
            "output_tokens": 900,
            "output_tokens_details": {"reasoning_tokens": 875},
        },
    }

    with pytest.raises(bedrock.BedrockIncompleteResponseError) as caught:
        bedrock._extract_mantle_text(payload, requested_max_tokens=900)

    assert caught.value.status == "completed"
    assert caught.value.reason == "max_output_tokens"


def test_claude_uses_seoul_runtime_and_global_model(monkeypatch):
    captured = {}

    class FakeRuntime:
        def invoke_model(self, **kwargs):
            captured.update(kwargs)
            return {"body": io.BytesIO(json.dumps({"content": [{"text": "평가"}]}).encode())}

    def fake_client(service_name, **kwargs):
        captured["service_name"] = service_name
        captured["region_name"] = kwargs["region_name"]
        return FakeRuntime()

    monkeypatch.setattr(bedrock.boto3, "client", fake_client)

    result = bedrock.BedrockClaude(
        "claude-haiku-4-5-20251001-v1:0", region="ap-northeast-2"
    ).generate("채점", max_tokens=321, effort="none", thinking="disabled")

    payload = json.loads(captured["body"])
    assert captured["service_name"] == "bedrock-runtime"
    assert captured["region_name"] == "ap-northeast-2"
    assert captured["modelId"] == "global.anthropic.claude-haiku-4-5-20251001-v1:0"
    assert payload["max_tokens"] == 321
    assert "output_config" not in payload
    assert payload["thinking"] == {"type": "disabled"}
    assert result == "평가"
