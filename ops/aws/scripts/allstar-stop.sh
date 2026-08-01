#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

require_root
load_allstar_env

log "종료 전 Prometheus 스냅샷을 생성합니다."
if ! "${SCRIPT_DIR}/prometheus-snapshot.sh"; then
  log "경고: Prometheus 스냅샷 생성에 실패했지만 종료를 계속합니다."
fi

if [[ -n "${S3_BUCKET:-}" ]]; then
  log "종료 전 로그·보고서·스냅샷 최종 동기화를 실행합니다."
  if ! "${SCRIPT_DIR}/s3-sync.sh" shutdown; then
    log "경고: S3 최종 동기화에 실패했습니다. EC2 종료 전에 수동 확인이 필요합니다."
  fi
fi

log "AllStar 컨테이너를 종료합니다."
allstar_compose down --remove-orphans
