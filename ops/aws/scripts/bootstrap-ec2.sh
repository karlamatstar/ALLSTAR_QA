#!/usr/bin/env bash
set -Eeuo pipefail

[[ "$(id -u)" -eq 0 ]] || {
  printf '[AllStar] 오류: sudo 또는 root 권한으로 실행해 주세요.\n' >&2
  exit 1
}

PROJECT_ROOT="${ALLSTAR_PROJECT_ROOT:-/opt/allstar}"
REPO_URL="${ALLSTAR_REPO_URL:-https://github.com/karlamatstar/ALLSTAR_QA.git}"
DEPLOY_BRANCH="${ALLSTAR_DEPLOY_BRANCH:-main}"

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates curl git gnupg jq tar unzip util-linux

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
. /etc/os-release
printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu %s stable\n' \
  "$(dpkg --print-architecture)" "${VERSION_CODENAME}" \
  > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y --no-install-recommends \
  docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker

arch="$(uname -m)"
case "${arch}" in
  x86_64) aws_arch=x86_64 ;;
  aarch64|arm64) aws_arch=aarch64 ;;
  *) printf '[AllStar] 오류: 지원하지 않는 CPU 아키텍처입니다: %s\n' "${arch}" >&2; exit 1 ;;
esac
tmp_dir="$(mktemp -d)"
trap 'rm -rf -- "${tmp_dir}"' EXIT
curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-${aws_arch}.zip" \
  -o "${tmp_dir}/awscliv2.zip"
unzip -q "${tmp_dir}/awscliv2.zip" -d "${tmp_dir}"
if command -v aws >/dev/null 2>&1; then
  "${tmp_dir}/aws/install" --update
else
  "${tmp_dir}/aws/install"
fi

if [[ -d "${PROJECT_ROOT}/.git" ]]; then
  git -C "${PROJECT_ROOT}" fetch origin "${DEPLOY_BRANCH}"
  git -C "${PROJECT_ROOT}" checkout "${DEPLOY_BRANCH}"
  git -C "${PROJECT_ROOT}" pull --ff-only origin "${DEPLOY_BRANCH}"
else
  git clone --branch "${DEPLOY_BRANCH}" --single-branch "${REPO_URL}" "${PROJECT_ROOT}"
fi

install -d -m 0700 /etc/allstar
if [[ ! -f /etc/allstar/allstar.env ]]; then
  install -m 0600 "${PROJECT_ROOT}/ops/aws/allstar.env.example" /etc/allstar/allstar.env
fi
if [[ ! -f /etc/allstar/duckdns.env ]]; then
  install -m 0600 "${PROJECT_ROOT}/ops/aws/duckdns.env.example" /etc/allstar/duckdns.env
fi

install -m 0644 "${PROJECT_ROOT}/ops/aws/systemd/allstar.service" /etc/systemd/system/allstar.service
install -m 0644 "${PROJECT_ROOT}/ops/aws/systemd/allstar-duckdns-update.service" \
  /etc/systemd/system/allstar-duckdns-update.service
install -m 0644 "${PROJECT_ROOT}/ops/aws/systemd/allstar-s3-sync.service" \
  /etc/systemd/system/allstar-s3-sync.service
install -m 0644 "${PROJECT_ROOT}/ops/aws/systemd/allstar-s3-sync.timer" \
  /etc/systemd/system/allstar-s3-sync.timer

chmod 0755 "${PROJECT_ROOT}"/ops/aws/scripts/*.sh
systemctl daemon-reload
systemctl enable allstar.service allstar-duckdns-update.service \
  allstar-s3-sync.service allstar-s3-sync.timer

printf '\n[AllStar] EC2 기본 설치가 완료되었습니다.\n'
printf '1) sudo nano /etc/allstar/allstar.env\n'
printf '2) sudo nano /etc/allstar/duckdns.env\n'
printf '3) sudo systemctl start allstar-duckdns-update.service\n'
printf '4) sudo systemctl start allstar.service\n'
printf '5) sudo systemctl start allstar-s3-sync.timer\n'
