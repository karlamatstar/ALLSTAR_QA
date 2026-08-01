from tools.scripts import run_validation_tests


def test_validation_report_creates_directories_on_fresh_output(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(run_validation_tests, "PROJECT_ROOT", tmp_path)

    report = run_validation_tests.create_chaos_defect_report("", "")

    assert report == (
        tmp_path
        / "_OUTPUT"
        / "reports"
        / "defects"
        / "chaos"
        / "defect_report.md"
    )
    assert report.is_file()
    assert list(
        (tmp_path / "_OUTPUT" / "logs" / "ai_agent" / "chaos").glob(
            "defect_report_*.md"
        )
    )
