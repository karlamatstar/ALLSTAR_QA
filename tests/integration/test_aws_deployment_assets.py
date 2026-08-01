from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AWS_COMPOSE = (ROOT / "compose.aws.yml").read_text(encoding="utf-8")
CADDYFILE = (ROOT / "ops" / "aws" / "Caddyfile").read_text(encoding="utf-8")


def test_aws_compose_exposes_only_caddy_ports():
    assert AWS_COMPOSE.count("ports: !reset []") == 12
    assert "${ALLSTAR_HTTP_PORT:-80}:80" in AWS_COMPOSE
    assert "${ALLSTAR_HTTPS_PORT:-443}:443" in AWS_COMPOSE
    assert "8000:8000" not in AWS_COMPOSE
    assert "8501:8501" not in AWS_COMPOSE
    assert "3000:3000" not in AWS_COMPOSE
    assert "9090:9090" not in AWS_COMPOSE


def test_aws_compose_persists_operational_data_and_pins_images():
    assert "/output:/srv/app/_OUTPUT" in AWS_COMPOSE
    assert "/prometheus:/prometheus" in AWS_COMPOSE
    assert "/grafana:/var/lib/grafana" in AWS_COMPOSE
    assert "/caddy/data:/data" in AWS_COMPOSE
    assert "prom/prometheus:v3.10.0" in AWS_COMPOSE
    assert "grafana/grafana:13.1.0" in AWS_COMPOSE
    assert "caddy:2.11.4-alpine" in AWS_COMPOSE
    assert ":latest" not in AWS_COMPOSE


def test_caddy_keeps_grafana_subpath_and_routes_dashboard():
    assert "redir @mountedGrafana /grafana/ 308" in CADDYFILE
    assert "handle /grafana/*" in CADDYFILE
    assert "reverse_proxy grafana:3000" in CADDYFILE
    assert "reverse_proxy streamlit:8501" in CADDYFILE
    assert "handle_path /grafana/*" not in CADDYFILE


def test_service_control_token_is_required_in_aws_compose():
    assert AWS_COMPOSE.count(
        "SERVICE_CONTROL_TOKEN: ${SERVICE_CONTROL_TOKEN:?SERVICE_CONTROL_TOKEN is required}"
    ) == 2
    assert "local-dev-service-control-token" not in AWS_COMPOSE


def test_automation_files_do_not_embed_secret_values():
    env_example = (ROOT / "ops" / "aws" / "allstar.env.example").read_text(encoding="utf-8")
    duckdns_example = (ROOT / "ops" / "aws" / "duckdns.env.example").read_text(
        encoding="utf-8"
    )
    assert "OPENAI_API_KEY=" not in env_example
    assert "ANTHROPIC_API_KEY=" not in env_example
    assert "BEDROCK_RUNTIME_REGION=ap-northeast-2" in env_example
    assert "BEDROCK_MANTLE_REGION=us-west-2" in env_example
    assert "SERVICE_CONTROL_TOKEN=\n" in env_example
    assert "GRAFANA_ADMIN_PASSWORD=\n" in env_example
    assert "DUCKDNS_TOKEN=\n" in duckdns_example


def test_s3_sync_has_changed_only_and_no_delete_policy():
    script = (ROOT / "ops" / "aws" / "scripts" / "s3-sync.sh").read_text(
        encoding="utf-8"
    )
    assert "aws s3 sync" in script
    assert "--delete" not in script
    assert '--exclude ".env"' in script
    assert "flock -n" in script
    assert "find \"${watch_roots[@]}\" -type f -newer" in script
    assert "변경된 백업 대상이 없어 S3 요청을 건너뜁니다" in script
    assert 'mv -f -- "${run_started}" "${last_success}"' in script


def test_systemd_timer_is_daily_and_persistent():
    timer = (ROOT / "ops" / "aws" / "systemd" / "allstar-s3-sync.timer").read_text(
        encoding="utf-8"
    )
    assert "OnCalendar=daily" in timer
    assert "Persistent=true" in timer


def test_duckdns_uses_imdsv2_without_logging_token_and_waits_for_dns():
    script = (ROOT / "ops" / "aws" / "scripts" / "duckdns-update.sh").read_text(
        encoding="utf-8"
    )
    assert "/latest/api/token" in script
    assert "X-aws-ec2-metadata-token" in script
    assert "curl --fail --silent --show-error --config -" in script
    assert '"https://www.duckdns.org/update"\\nget\\ndata = ' in script
    assert "getent ahostsv4" in script
    assert "for attempt in 1 2 3" in script
    assert not any(
        "${DUCKDNS_TOKEN}" in line and "printf '[AllStar]" in line
        for line in script.splitlines()
    )
