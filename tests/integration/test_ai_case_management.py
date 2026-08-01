import json
from pathlib import Path

from allstar.ui.dashboard import views


def test_active_ai_cases_are_three_representative_scenarios():
    root = Path(__file__).resolve().parents[2]
    active_path = root / "src" / "allstar" / "ai_agent" / "evaluation" / "test_cases.json"
    archive_path = (
        root / "src" / "allstar" / "ai_agent" / "evaluation"
        / "archive" / "test_cases_6_2026-07-25.json"
    )

    active = json.loads(active_path.read_text(encoding="utf-8"))
    archive = json.loads(archive_path.read_text(encoding="utf-8"))

    assert [case["case_id"] for case in active] == ["TC-001", "TC-021", "TC-026"]
    assert len(archive) == 6
    assert {case["test_type"] for case in active} == {"Happy", "Edge", "Negative"}


def test_ai_case_change_archive_preserves_current_list(tmp_path, monkeypatch):
    cases_path = tmp_path / "test_cases.json"
    monkeypatch.setattr(views, "AI_CASES_PATH", cases_path)
    cases = [{"case_id": "TC-001", "category": "정확성", "test_type": "Happy"}]

    archive_path = views._archive_ai_case_document(cases)

    assert archive_path.parent == tmp_path / "archive" / "revisions"
    assert archive_path.name.startswith("test_cases_before_change_")
    assert json.loads(archive_path.read_text(encoding="utf-8")) == cases


def test_docker_case_archive_uses_shared_output_root(tmp_path, monkeypatch):
    monkeypatch.setattr(views, "TEST_CASE_ARCHIVE_ROOT", str(tmp_path))

    archive_path = views._archive_ai_case_document([{"case_id": "TC-001"}])

    assert archive_path.parent == tmp_path / "ai_agent" / "revisions"


def test_ai_case_edit_ui_preserves_id_and_locks_changes_during_run():
    source = Path(views.__file__).read_text(encoding="utf-8")

    assert "기존 AI 에이전트 테스트케이스 확인·수정" in source
    assert 'text_input("테스트케이스 ID", value=selected_id, disabled=True)' in source
    assert "_archive_ai_case_document(cases)" in source
    assert 'submitted = st.form_submit_button("테스트케이스 저장", type="primary", disabled=add_disabled)' in source
    assert "DASHBOARD_TEST_CASE_LIMIT = 10" in source
    assert "len(cases) >= DASHBOARD_TEST_CASE_LIMIT" in source
    assert "len(cases) - len(delete_ids) >= 1" in source
    assert "최소 1개의 테스트케이스는 유지해야 합니다." in source
    assert '"--limit"' in source
