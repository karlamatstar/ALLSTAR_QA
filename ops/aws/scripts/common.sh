#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${ALLSTAR_PROJECT_ROOT:-$(cd -- "${SCRIPT_DIR}/../../.." && pwd)}"
ALLSTAR_ENV_FILE="${ALLSTAR_ENV_FILE:-/etc/allstar/allstar.env}"

log() {
  printf '[AllStar] %s\n' "$*"
}

fail() {
  printf '[AllStar] 오류: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "필수 명령을 찾을 수 없습니다: $1"
}

require_root() {
  [[ "$(id -u)" -eq 0 ]] || fail "sudo 또는 root 권한으로 실행해 주세요."
}

load_allstar_env() {
  [[ -f "${ALLSTAR_ENV_FILE}" ]] || fail "환경 파일이 없습니다: ${ALLSTAR_ENV_FILE}"
  set -a
  # shellcheck disable=SC1090
  source "${ALLSTAR_ENV_FILE}"
  set +a
  ALLSTAR_COMPOSE_PROJECT="${ALLSTAR_COMPOSE_PROJECT:-allstar}"
  ALLSTAR_DATA_ROOT="${ALLSTAR_DATA_ROOT:-/opt/allstar-data}"
  export ALLSTAR_COMPOSE_PROJECT ALLSTAR_DATA_ROOT
}

require_value() {
  local name="$1"
  [[ -n "${!name:-}" ]] || fail "${name} 값이 비어 있습니다."
}

allstar_compose() {
  docker compose \
    --project-name "${ALLSTAR_COMPOSE_PROJECT}" \
    --env-file "${ALLSTAR_ENV_FILE}" \
    -f "${PROJECT_ROOT}/compose.yml" \
    -f "${PROJECT_ROOT}/compose.aws.yml" \
    "$@"
}

prepare_data_directories() {
  install -d -m 0750 \
    "${ALLSTAR_DATA_ROOT}/output/logs" \
    "${ALLSTAR_DATA_ROOT}/output/reports" \
    "${ALLSTAR_DATA_ROOT}/output/archives" \
    "${ALLSTAR_DATA_ROOT}/prometheus" \
    "${ALLSTAR_DATA_ROOT}/prometheus-backups" \
    "${ALLSTAR_DATA_ROOT}/grafana" \
    "${ALLSTAR_DATA_ROOT}/caddy/data" \
    "${ALLSTAR_DATA_ROOT}/caddy/config"

  chown -R 65534:65534 "${ALLSTAR_DATA_ROOT}/prometheus"
  chown -R 472:472 "${ALLSTAR_DATA_ROOT}/grafana"
}
