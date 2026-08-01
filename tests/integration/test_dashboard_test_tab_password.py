from pathlib import Path

from allstar.ui.dashboard.access_control import (
    DEFAULT_TEST_TAB_PASSWORD,
    TEST_TAB_PASSWORD_ENV,
    configured_test_tab_password,
    matches_test_tab_password,
)


ROOT = Path(__file__).resolve().parents[2]
APP = (ROOT / "src" / "allstar" / "ui" / "dashboard" / "streamlit_app.py").read_text(encoding="utf-8")
VIEWS = (ROOT / "src" / "allstar" / "ui" / "dashboard" / "views.py").read_text(encoding="utf-8")
COMPOSE = (ROOT / "compose.yml").read_text(encoding="utf-8")
ENV_EXAMPLE = (ROOT / ".env.example").read_text(encoding="utf-8")


def test_test_tab_password_defaults_to_1234(monkeypatch):
    monkeypatch.delenv(TEST_TAB_PASSWORD_ENV, raising=False)

    assert configured_test_tab_password() == DEFAULT_TEST_TAB_PASSWORD == "1234"
    assert matches_test_tab_password("1234") is True
    assert matches_test_tab_password("4321") is False


def test_test_tab_password_can_be_changed_by_environment(monkeypatch):
    monkeypatch.setenv(TEST_TAB_PASSWORD_ENV, "9876")

    assert matches_test_tab_password("1234") is False
    assert matches_test_tab_password("9876") is True


def test_three_top_test_tabs_are_visible_and_protect_actual_execution():
    assert "_render_test_tab_password_gate" not in APP
    assert "_render_password_protected_test_tab" not in APP
    assert APP.index("with tab_k6_load:") < APP.index("with tab_ai_chat:")
    assert "render_k6_load_test()" in APP
    assert "render_ai_testcases()" in APP
    assert "render_voc_testcases()" in APP

    assert "def _required_execution_password" in VIEWS
    assert 'type="password"' in VIEWS
    assert "matches_test_tab_password(password)" in VIEWS
    assert 'with st.form(f"execution_password_form_{safe_key}"):' in VIEWS
    assert 'st.columns([4, 1], gap="small", vertical_alignment="bottom")' in VIEWS
    assert 'submit_column.form_submit_button(' in VIEWS
    assert '"확인",' in VIEWS
    assert "if submitted:" in VIEWS
    assert "execution_password_verified_{safe_key}" in VIEWS
    assert "execution_password_error_{safe_key}" in VIEWS
    assert "비밀번호를 입력한 뒤 확인 버튼을 누르거나 Enter 키를 누르면 적용됩니다." in VIEWS
    for key in ("k6_api_performance", "ai_testcases", "voc_testcases"):
        assert f'"{key}"' in VIEWS
    assert VIEWS.count("실행 비밀번호 입력이 필요함을 이해했습니다.") == 3


def test_unchecking_required_confirmation_clears_password_and_verification_state():
    section = VIEWS[VIEWS.index("def _required_execution_password"):VIEWS.index("def _render_dataframe")]

    assert "if not confirmed:" in section
    assert "st.session_state.pop(input_key, None)" in section
    assert "st.session_state.pop(verified_key, None)" in section
    assert "st.session_state.pop(error_key, None)" in section
    assert section.index("if not confirmed:") < section.index("with st.form")


def test_docker_streamlit_receives_the_configurable_demo_password():
    setting = "DASHBOARD_TEST_TABS_PASSWORD: ${DASHBOARD_TEST_TABS_PASSWORD:-1234}"

    assert setting in COMPOSE
    assert "DASHBOARD_TEST_TABS_PASSWORD=1234" in ENV_EXAMPLE


def test_ai_chat_fault_buttons_use_independent_password_confirmation():
    section = VIEWS[VIEWS.index("def render_ai_chat"):VIEWS.index("def _render_profile_cards")]

    assert "from allstar.ui.dashboard.access_control import matches_test_tab_password" in VIEWS
    assert "matches_test_tab_password(password)" in VIEWS
    assert '"ai_fault_test"' in VIEWS
    assert "비밀번호를 입력해야만 장애 상황 시험을 실행할 수 있습니다." in VIEWS
    assert "not fault_password_confirmed" in VIEWS
    assert '_required_execution_password(\n            True,\n            "ai_fault_test"' in section
    assert '_required_execution_password(\n            api_confirmed,\n            "ai_fault_test"' not in section
    assert "ai_fault_test_access" not in VIEWS
    assert "test_tab_access_" not in VIEWS
    assert "쿠키" not in VIEWS
