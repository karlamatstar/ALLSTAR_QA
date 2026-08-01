#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

require_root
require_command git
load_allstar_env

branch="${ALLSTAR_DEPLOY_BRANCH:-main}"
current="$(git -C "${PROJECT_ROOT}" branch --show-current)"
[[ "${current}" == "${branch}" ]] \
  || fail "현재 브랜치가 ${branch}가 아닙니다: ${current}"
[[ -z "$(git -C "${PROJECT_ROOT}" status --porcelain)" ]] \
  || fail "작업 폴더에 커밋되지 않은 변경이 있습니다."

log "${branch} 최신 커밋을 가져옵니다."
git -C "${PROJECT_ROOT}" pull --ff-only origin "${branch}"
"${SCRIPT_DIR}/allstar-start.sh"
