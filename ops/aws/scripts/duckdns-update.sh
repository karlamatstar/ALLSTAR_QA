#!/usr/bin/env bash
set -Eeuo pipefail

DUCKDNS_ENV_FILE="${DUCKDNS_ENV_FILE:-/etc/allstar/duckdns.env}"
[[ -f "${DUCKDNS_ENV_FILE}" ]] || {
  printf '[AllStar] 오류: DuckDNS 환경 파일이 없습니다: %s\n' "${DUCKDNS_ENV_FILE}" >&2
  exit 1
}

set -a
# shellcheck disable=SC1090
source "${DUCKDNS_ENV_FILE}"
set +a

[[ -n "${DUCKDNS_DOMAIN:-}" ]] || {
  printf '[AllStar] 오류: DUCKDNS_DOMAIN 값이 비어 있습니다.\n' >&2
  exit 1
}
[[ -n "${DUCKDNS_TOKEN:-}" ]] || {
  printf '[AllStar] 오류: DUCKDNS_TOKEN 값이 비어 있습니다.\n' >&2
  exit 1
}

domain="${DUCKDNS_DOMAIN%.duckdns.org}"
if [[ -n "${DUCKDNS_IPV4:-}" ]]; then
  public_ip="${DUCKDNS_IPV4}"
else
  imds_token="$(
    curl --fail --silent --show-error --max-time 3 \
      -X PUT \
      -H 'X-aws-ec2-metadata-token-ttl-seconds: 60' \
      http://169.254.169.254/latest/api/token
  )"
  public_ip="$(
    curl --fail --silent --show-error --max-time 3 \
      -H "X-aws-ec2-metadata-token: ${imds_token}" \
      http://169.254.169.254/latest/meta-data/public-ipv4
  )"
fi

[[ "${public_ip}" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]] || {
  printf '[AllStar] 오류: EC2 공인 IPv4 형식이 올바르지 않습니다.\n' >&2
  exit 1
}

response=""
for attempt in 1 2 3; do
  if response="$(
    printf 'url = "https://www.duckdns.org/update"\nget\ndata = "domains=%s&token=%s&ip=%s&verbose=true"\n' \
      "${domain}" "${DUCKDNS_TOKEN}" "${public_ip}" \
      | curl --fail --silent --show-error --config -
  )" && [[ "$(head -n 1 <<<"${response}")" == "OK" ]]; then
    break
  fi
  response=""
  sleep $((attempt * 2))
done
[[ -n "${response}" ]] || {
  printf '[AllStar] 오류: DuckDNS 갱신에 실패했습니다.\n' >&2
  exit 1
}

fqdn="${domain}.duckdns.org"
for _ in {1..12}; do
  resolved="$(
    getent ahostsv4 "${fqdn}" 2>/dev/null \
      | awk 'NR == 1 { print $1 }'
  )"
  if [[ "${resolved}" == "${public_ip}" ]]; then
    printf '[AllStar] DuckDNS 갱신 완료: %s -> %s\n' "${fqdn}" "${public_ip}"
    exit 0
  fi
  sleep 5
done

printf '[AllStar] 오류: DuckDNS 조회 주소가 60초 안에 EC2 공인 IPv4와 일치하지 않았습니다.\n' >&2
exit 1
