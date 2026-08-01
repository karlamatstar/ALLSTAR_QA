#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

require_root
require_command docker
require_command curl
require_command aws
load_allstar_env

for name in \
  ALLSTAR_DOMAIN ALLSTAR_SITE_ADDRESS ALLSTAR_PUBLIC_URL \
  SERVICE_CONTROL_TOKEN GRAFANA_ADMIN_PASSWORD; do
  require_value "${name}"
done

aws sts get-caller-identity >/dev/null \
  || fail "EC2 IAM 역할을 포함한 AWS 자격 증명을 확인할 수 없습니다."

[[ "${SERVICE_CONTROL_TOKEN}" != "local-dev-service-control-token" ]] \
  || fail "AWS에서는 로컬 개발용 SERVICE_CONTROL_TOKEN을 사용할 수 없습니다."
[[ "${ALLSTAR_PUBLIC_URL}" == https://* || "${ALLSTAR_SITE_ADDRESS}" == http://localhost* ]] \
  || fail "공개 운영 주소는 https:// 로 시작해야 합니다."

prepare_data_directories
allstar_compose config --quiet

log "AWS 전용 이미지를 빌드하고 서비스를 시작합니다."
allstar_compose up -d --build --remove-orphans

deadline=$((SECONDS + 240))
expected="$(allstar_compose config --services | wc -l | tr -d ' ')"
while (( SECONDS < deadline )); do
  running="$(allstar_compose ps --services --status running | wc -l | tr -d ' ')"
  if [[ "${running}" == "${expected}" ]]; then
    if allstar_compose exec -T caddy \
      wget -qO- http://streamlit:8501/_stcore/health >/dev/null \
      && allstar_compose exec -T caddy \
        wget -qO- http://grafana:3000/grafana/api/health >/dev/null; then
      log "전체 ${expected}개 서비스와 대시보드·Grafana가 준비되었습니다."
      log "공개 주소: ${ALLSTAR_PUBLIC_URL}"
      exit 0
    fi
  fi
  sleep 3
done

allstar_compose ps
fail "240초 안에 전체 서비스가 실행 상태가 되지 않았습니다."
