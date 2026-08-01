"""VOC 실행 환경에서 공통으로 사용하는 모델명과 데이터 경로."""

from __future__ import annotations

import os

from allstar.shared.paths import VOC_DATA_ROOT
from allstar.voc.runtime.env_loader import load_env


load_env()

MODEL_SUMMARY = os.environ.get(
    "OPENAI_MODEL",
    os.environ.get("A2A_MODEL_SUMMARY", "openai.gpt-5.6-luna"),
)
MODEL_POLICY = os.environ.get(
    "A2A_MODEL_POLICY",
    "global.anthropic.claude-sonnet-5",
)
DEFAULT_CSV = os.environ.get("A2A_VOC_CSV", str(VOC_DATA_ROOT / "voc.csv"))
