"""VOC 챗봇과 QA가 함께 사용하는 A~D 모델 프로필의 단일 원본."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    model: str
    reasoning: str
    thinking: str = "disabled"


@dataclass(frozen=True)
class ModelProfile:
    profile_id: str
    title: str
    summary: str
    generation: ModelSpec
    judge: ModelSpec
    recommended: bool = False

    def snapshot(self) -> dict:
        return asdict(self)


def _models() -> dict[str, ModelSpec]:
    return {
        "openai_generation": ModelSpec(
            "openai",
            os.getenv("VOC_OPENAI_GENERATION_MODEL", "openai.gpt-oss-20b"),
            os.getenv("VOC_OPENAI_GENERATION_REASONING", "none"),
        ),
        "openai_judge": ModelSpec(
            "openai",
            os.getenv("VOC_OPENAI_JUDGE_MODEL", "openai.gpt-oss-120b"),
            os.getenv("VOC_OPENAI_JUDGE_REASONING", "low"),
        ),
        "deepseek_generation": ModelSpec(
            "deepseek",
            os.getenv("VOC_DEEPSEEK_GENERATION_MODEL", "deepseek.v3.1"),
            "none",
        ),
        "deepseek_judge": ModelSpec(
            "deepseek",
            os.getenv("VOC_DEEPSEEK_JUDGE_MODEL", "deepseek.v3.2"),
            "none",
        ),
    }


def profiles() -> dict[str, ModelProfile]:
    model = _models()
    return {
        "A": ModelProfile(
            "A", "기본 권장", "OpenAI가 답변을 만들고 DeepSeek이 독립 평가",
            model["openai_generation"], model["deepseek_judge"], True,
        ),
        "B": ModelProfile(
            "B", "역방향 교차 평가", "DeepSeek이 답변을 만들고 OpenAI가 독립 평가",
            model["deepseek_generation"], model["openai_judge"],
        ),
        "C": ModelProfile(
            "C", "OpenAI 계열 비교", "OpenAI 안에서 생성 모델과 평가 모델을 분리",
            model["openai_generation"], model["openai_judge"],
        ),
        "D": ModelProfile(
            "D", "DeepSeek 계열 비교", "DeepSeek 안에서 생성 모델과 평가 모델을 분리",
            model["deepseek_generation"], model["deepseek_judge"],
        ),
    }


def get_profile(profile_id: str) -> ModelProfile:
    key = (profile_id or "A").upper()
    try:
        return profiles()[key]
    except KeyError as error:
        raise ValueError(f"지원하지 않는 모델 프로필: {profile_id}") from error


def public_profiles() -> list[dict]:
    return [profile.snapshot() for profile in profiles().values()]


def missing_keys(profile: ModelProfile) -> list[str]:
    """기존 API 호환 필드.

    Bedrock은 EC2 IAM 역할 또는 AWS 기본 자격 증명 체인을 호출 시점에 사용하므로
    프로필별 장기 API 키 누락 항목은 없다.
    """
    return []
