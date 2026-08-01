#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

require_root
require_command aws
require_command flock
require_command git
load_allstar_env
require_value AWS_REGION
require_value S3_BUCKET

exec 9>/run/lock/allstar-s3-sync.lock
if ! flock -n 9; then
  log "다른 S3 동기화가 진행 중이므로 이번 실행은 건너뜁니다."
  exit 0
fi

prepare_data_directories
state_dir="/var/lib/allstar-s3-sync"
install -d -m 0750 "${state_dir}"
last_success="${state_dir}/last-success"
watch_roots=(
  "${ALLSTAR_DATA_ROOT}/output/logs"
  "${ALLSTAR_DATA_ROOT}/output/reports"
  "${ALLSTAR_DATA_ROOT}/output/archives"
  "${ALLSTAR_DATA_ROOT}/prometheus-backups"
)
if [[ -f "${last_success}" ]] \
  && ! find "${watch_roots[@]}" -type f -newer "${last_success}" -print -quit | grep -q .; then
  log "마지막 성공 이후 변경된 백업 대상이 없어 S3 요청을 건너뜁니다."
  exit 0
fi

run_started="${state_dir}/run-started"
touch "${run_started}"

prefix="${S3_PREFIX:-allstar}"
prefix="${prefix#/}"
prefix="${prefix%/}"
base_uri="s3://${S3_BUCKET}/${prefix}"
sync_args=(
  --region "${AWS_REGION}"
  --only-show-errors
  --no-follow-symlinks
  --sse AES256
  --exclude ".env"
  --exclude ".env.*"
)

for folder in logs reports archives; do
  source_dir="${ALLSTAR_DATA_ROOT}/output/${folder}"
  [[ -d "${source_dir}" ]] || continue
  log "${folder} 변경분을 S3에 동기화합니다."
  aws s3 sync "${source_dir}" "${base_uri}/output/${folder}/" "${sync_args[@]}"
done

if compgen -G "${ALLSTAR_DATA_ROOT}/prometheus-backups/*" >/dev/null; then
  log "Prometheus 스냅샷 백업 변경분을 S3에 동기화합니다."
  aws s3 sync \
    "${ALLSTAR_DATA_ROOT}/prometheus-backups" \
    "${base_uri}/prometheus-backups/" \
    "${sync_args[@]}"
fi

manifest="$(mktemp)"
trap 'rm -f -- "${manifest}"' EXIT
commit="$(git -C "${PROJECT_ROOT}" rev-parse HEAD 2>/dev/null || printf unknown)"
printf 'timestamp=%s\ncommit=%s\ncompose_project=%s\nreason=%s\n' \
  "$(date --iso-8601=seconds)" \
  "${commit}" \
  "${ALLSTAR_COMPOSE_PROJECT}" \
  "${1:-scheduled}" > "${manifest}"
aws s3 cp \
  "${manifest}" \
  "${base_uri}/manifests/latest-sync.txt" \
  --region "${AWS_REGION}" \
  --only-show-errors \
  --sse AES256

mv -f -- "${run_started}" "${last_success}"
log "S3 동기화 완료: ${base_uri}"
