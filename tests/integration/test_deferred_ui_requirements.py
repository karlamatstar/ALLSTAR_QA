from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_voc_completion_wait_disables_every_profile_run_button():
    source = (ROOT / "src/allstar/ui/dashboard/views.py").read_text(encoding="utf-8")

    assert "disabled = running or completed_pending or not password_confirmed or not cases" in source
    assert "완료 상태 닫기 · 다음 테스트 준비" in source


def test_comparison_charts_use_distinct_color_families_and_line_styles():
    source = (ROOT / "src/allstar/ui/dashboard/views.py").read_text(encoding="utf-8")
    report_source = (
        ROOT / "src/allstar/ai_agent/evaluation/live_report_charts.py"
    ).read_text(encoding="utf-8")

    for color in ("#0072B2", "#E69F00", "#009E73", "#CC79A7"):
        assert color in source
    for dash in ('"solid"', '"dash"', '"dot"', '"dashdot"'):
        assert dash in source
    assert 'MODEL_COLORS = ("#0072B2", "#E69F00")' in report_source
