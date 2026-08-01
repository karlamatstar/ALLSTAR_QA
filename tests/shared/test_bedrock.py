import io
import json

from allstar.shared import bedrock


def test_model_ids_are_normalized_for_each_bedrock_surface():
    assert bedrock.normalize_gpt_model("gpt-5.6-luna") == "openai.gpt-5.6-luna"
    assert bedrock.normalize_gpt_model("openai.gpt-5.6-terra") == "openai.gpt-5.6-terra"
    assert (
        bedrock.normalize_claude_model("claude-sonnet-4-6")
        == "global.anthropic.claude-sonnet-4-6"
    )


def test_gpt_uses_signed_mantle_responses_endpoint(monkeypatch):
    captured = {}

    class FakeResponse:
        @staticmethod
        def raise_for_status():
            return None

        @staticmethod
        def json():
            return {"output": [{"content": [{"type": "output_text", "text": "응답"}]}]}

    def fake_post(url, *, content, headers, timeout):
        captured.update(url=url, content=content, headers=headers, timeout=timeout)
        return FakeResponse()

    monkeypatch.setattr(bedrock, "_signed_headers", lambda *_args: {"Authorization": "signed"})
    monkeypatch.setattr(bedrock.httpx, "post", fake_post)

    result = bedrock.BedrockGPT("gpt-5.6-luna", region="us-west-2").generate(
        "질문", max_tokens=123, reasoning="none"
    )

    payload = json.loads(captured["content"])
    assert captured["url"] == "https://bedrock-mantle.us-west-2.api.aws/v1/responses"
    assert captured["headers"]["Authorization"] == "signed"
    assert payload["model"] == "openai.gpt-5.6-luna"
    assert payload["store"] is False
    assert "reasoning" not in payload
    assert result == "응답"


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
        "claude-sonnet-5", region="ap-northeast-2"
    ).generate("채점", max_tokens=321, effort="low", thinking="disabled")

    payload = json.loads(captured["body"])
    assert captured["service_name"] == "bedrock-runtime"
    assert captured["region_name"] == "ap-northeast-2"
    assert captured["modelId"] == "global.anthropic.claude-sonnet-5"
    assert payload["max_tokens"] == 321
    assert payload["output_config"] == {"effort": "low"}
    assert payload["thinking"] == {"type": "disabled"}
    assert result == "평가"
