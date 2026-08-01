"""프로필에 지정된 독립 Judge로 VOC 공통 9항목·100점 평가를 수행한다."""

from __future__ import annotations

from typing import Any

from allstar.shared.model_profiles import ModelSpec
from allstar.shared.language import language_mismatch_reason, response_language_matches
from allstar.voc.evaluation.judge_prompt import (
    build_judge_prompt,
    decide_verdict,
    parse_judge_response,
)
from allstar.voc.evaluation.runtime_support import load_json


RUBRIC_VERSION = "voc_9x100_v1"


def _analysis_text(result: dict[str, Any] | str, elapsed_seconds: float | None = None) -> str:
    """실시간 파이프라인의 6단계 산출물을 테스트케이스 Judge와 같은 형식으로 묶는다."""
    if isinstance(result, str):
        return result
    elapsed = elapsed_seconds
    if elapsed is None:
        elapsed = result.get("elapsed_seconds")
    return (
        f"[Interpreter 의도]\n{result.get('intent_json', '{}')}\n\n"
        f"[Retriever 및 Agent 연계 추적]\n{result.get('trace', '')}\n\n"
        f"[Summarizer 요약]\n{result.get('summary', '')}\n\n"
        f"[Evaluator 평가]\n{result.get('eval_json', '{}')}\n\n"
        f"[Critic 검토]\n{result.get('summary_critic_json', '{}')}\n\n"
        f"[Improver 정책 개선안]\n{result.get('policy', '')}\n\n"
        f"[전체 응답시간]\n{elapsed if elapsed is not None else '기록 없음'}초"
    )


async def evaluate(
    question: str,
    result: dict[str, Any] | str,
    spec: ModelSpec,
    elapsed_seconds: float | None = None,
) -> dict[str, Any]:
    rubric = load_json("judge_rubric.json")
    prompt = build_judge_prompt(question, _analysis_text(result, elapsed_seconds), rubric)
    if spec.provider == "openai":
        from allstar.shared.bedrock import BedrockGPT

        text = await BedrockGPT(spec.model).generate_async(
            prompt,
            reasoning=spec.reasoning,
            verbosity="low",
            max_tokens=2200,
        )
    elif spec.provider == "anthropic":
        from allstar.shared.bedrock import BedrockClaude

        text = await BedrockClaude(spec.model).generate_async(
            prompt,
            max_tokens=2200,
            effort=spec.reasoning,
            thinking=spec.thinking,
        )
    else:
        raise ValueError(f"지원하지 않는 Judge 제공자: {spec.provider}")

    parsed = parse_judge_response(text, rubric)
    if parsed is None:
        raise ValueError("Judge 응답에서 유효한 9항목 채점 JSON을 찾지 못했습니다.")
    final_answer = result.get("answer", "") if isinstance(result, dict) else str(result)
    language_guard_failed = bool(
        isinstance(result, dict) and (result.get("language_guard") or {}).get("matched") is False
    )
    if language_guard_failed or not response_language_matches(question, final_answer):
        parsed["immediate_hold"] = True
        parsed["hold_reason"] = language_mismatch_reason(question)
        parsed["rationale"] = (
            f"{parsed['hold_reason']} 언어 일치는 최종 사용자 응답의 필수 조건이므로 즉시 보류합니다."
        )
    verdict = decide_verdict(parsed["total"], parsed["immediate_hold"], rubric)
    return {
        "schema_version": 2,
        "rubric_version": RUBRIC_VERSION,
        "rubric_max_score": rubric["total_max_score"],
        "scores": parsed["scores"],
        "reasons": parsed["reasons"],
        "total": parsed["total"],
        "verdict": verdict,
        "immediate_hold": parsed["immediate_hold"],
        "hold_reason": parsed["hold_reason"],
        "rationale": parsed["rationale"],
        "provider": spec.provider,
        "model": spec.model,
        "reasoning": spec.reasoning,
        "thinking": spec.thinking,
    }
