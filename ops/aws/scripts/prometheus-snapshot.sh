#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

require_root
require_command jq
require_command tar
require_command sha256sum
load_allstar_env
prepare_data_directories

if ! allstar_compose ps --services --status running | grep -qx prometheus; then
  log "Prometheus가 실행 중이 아니므로 스냅샷을 건너뜁니다."
  exit 0
fi

response="$(
  allstar_compose exec -T prometheus \
    wget -qO- --post-data='' http://127.0.0.1:9090/api/v1/admin/tsdb/snapshot
)"
snapshot_name="$(jq -er '.data.name' <<<"${response}")"
snapshot_root="${ALLSTAR_DATA_ROOT}/prometheus/snapshots"
snapshot_path="${snapshot_root}/${snapshot_name}"
[[ -d "${snapshot_path}" ]] || fail "Prometheus 스냅샷 디렉터리를 찾을 수 없습니다."

archive="${ALLSTAR_DATA_ROOT}/prometheus-backups/prometheus-${snapshot_name}.tar.gz"
tar -C "${snapshot_root}" -czf "${archive}" "${snapshot_name}"
sha256sum "${archive}" > "${archive}.sha256"

case "${snapshot_path}" in
  "${snapshot_root}/"*) rm -rf -- "${snapshot_path}" ;;
  *) fail "안전하지 않은 스냅샷 경로입니다." ;;
esac

log "Prometheus 스냅샷 보관 완료: ${archive}"
