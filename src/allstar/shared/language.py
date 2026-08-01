"""사용자 질문과 최종 사용자 응답의 주 언어를 일치시키는 공통 안전장치."""

from __future__ import annotations

import re


_HANGUL_RE = re.compile(r"[가-힣]")
_LATIN_RE = re.compile(r"[A-Za-z]")


def primary_language(text: str) -> str:
    """현재 서비스가 지원하는 한국어·영어 중 텍스트의 주 언어를 반환한다."""
    value = text or ""
    if _HANGUL_RE.search(value):
        return "ko"
    if _LATIN_RE.search(value):
        return "en"
    return "unknown"


def response_language_matches(question: str, response: str) -> bool:
    """질문의 식별 가능한 주 언어가 응답에도 포함되어 있는지 확인한다."""
    question_language = primary_language(question)
    if question_language == "unknown":
        return True
    return primary_language(response) == question_language


def language_mismatch_reason(question: str) -> str:
    language = primary_language(question)
    expected = {"ko": "한국어", "en": "영어"}.get(language, "질문과 동일한 언어")
    return f"사용자 질문은 {expected}이지만 최종 답변이 같은 언어로 작성되지 않았습니다."


def localized_language_guard_message(question: str) -> str:
    """언어가 어긋난 모델 출력을 사용자에게 그대로 노출하지 않을 때 쓸 안내문."""
    if primary_language(question) == "en":
        return "The response language did not match your question. Please try again."
    return "답변 언어가 질문과 일치하지 않아 결과를 표시하지 않았습니다. 다시 시도해 주세요."


def localized_service_error_message(question: str) -> str:
    if primary_language(question) == "en":
        return "The AI service is temporarily unavailable. Please try again later. (503 Service Unavailable)"
    return "현재 API 서버 점검 중이거나 일시적인 통신 장애가 발생했습니다. 잠시 후 다시 시도해 주세요. (503 Service Unavailable)"
