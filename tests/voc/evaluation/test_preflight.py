"""수강 과제·발표 사전 점검 도구의 단위 테스트."""

from allstar.voc.runtime import preflight


def test_collect_checks_reports_bedrock_regions_without_api_keys(monkeypatch):
    monkeypatch.setenv("BEDROCK_RUNTIME_REGION", "ap-northeast-2")
    monkeypatch.setenv("BEDROCK_MANTLE_REGION", "us-west-2")
    monkeypatch.setattr(preflight, "_port_open", lambda _port: False)

    report = preflight.format_report(preflight.collect_checks())

    assert "BEDROCK_RUNTIME_REGION" in report
    assert "ap-northeast-2" in report
    assert "OPENAI_API_KEY" not in report


def test_agent_ports_are_informational(monkeypatch):
    monkeypatch.setattr(preflight, "_port_open", lambda _port: False)

    checks = preflight.collect_checks()
    agent_checks = [check for check in checks if check.category == "에이전트"]

    assert len(agent_checks) == 6
    assert all(not check.required for check in agent_checks)
    assert all(not check.ok for check in agent_checks)


def test_report_marks_required_failure():
    checks = [preflight.Check("파일", "voc.csv", False, True, "없음")]
    report = preflight.format_report(checks)

    assert "[실패]" in report
    assert "기본 실행 준비: 미완료" in report
