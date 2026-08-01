import os

from dotenv import load_dotenv
from allstar.shared.paths import AI_AGENT_LOG_ROOT, PROJECT_ROOT

AI_AGENT_LIVE_LOG_ROOT = AI_AGENT_LOG_ROOT / "live"
CONVERSATION_LOG_DIR = AI_AGENT_LIVE_LOG_ROOT / "conversations"
JUDGMENT_LOG_DIR = AI_AGENT_LIVE_LOG_ROOT / "judgments"
CONVERSATION_LOG_DIR.mkdir(parents=True, exist_ok=True)
JUDGMENT_LOG_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(PROJECT_ROOT / ".env")

AI_CHAT_MODEL = os.getenv("AI_CHAT_MODEL", "openai.gpt-oss-20b")
AI_JUDGE_MODEL = os.getenv("AI_JUDGE_MODEL", "openai.gpt-oss-120b")
# 기존 보고서·화면 코드와의 호환 이름입니다.
OPENAI_MODEL = AI_CHAT_MODEL

JIRA_URL = os.getenv("JIRA_URL")
JIRA_USER = os.getenv("JIRA_USER")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "BUG")
JIRA_EPIC_KEY = os.getenv("JIRA_EPIC_KEY", "BUG-1")
JIRA_SPRINT_ID = os.getenv("JIRA_SPRINT_ID", "36")

def validate_config() -> None:
    if not AI_CHAT_MODEL or not AI_JUDGE_MODEL:
        raise ValueError("AI_CHAT_MODEL과 AI_JUDGE_MODEL을 설정해야 합니다.")
