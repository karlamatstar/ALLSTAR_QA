# AWS EC2 Docker 배포 실행 기준

> 작성일: 2026-07-25
> 적용 브랜치: `main`
> 기준 도메인: `allstarqa.duckdns.org`
> 상태: **AWS 배포 코드·로컬 Docker·실제 EC2 최초 배포 검증 완료**

## 1. 배포 구조

```text
방문자 브라우저
  ↓ 80·443
Caddy 2.11.4
  ├─ /          → Streamlit:8501
  └─ /grafana/  → Grafana:3000

Docker 내부
  ├─ AI API:8000
  ├─ VOC API:8100와 에이전트:6001~6006
  ├─ K6 Runner:8200
  ├─ Prometheus:9090
  └─ service-control:8300

EC2 EBS /opt/allstar-data
  ├─ output
  ├─ prometheus
  ├─ grafana
  └─ caddy
        ↓ 매일 변경분·종료 전 최종본
      S3
```

로컬 `compose.yml`은 그대로 유지한다. AWS에서는 `compose.aws.yml`을 함께 적용해 기존 호스트 포트를 `!reset []`으로 제거한다. 호스트에 공개되는 컨테이너 포트는 Caddy의 `80`·`443`뿐이다.

## 2. 구현 파일

| 파일 | 역할 |
|---|---|
| `compose.aws.yml` | 내부 포트 차단, Caddy, 고정 이미지, EBS 영구 경로 |
| `ops/aws/Caddyfile` | HTTPS 자동 발급과 Streamlit·Grafana 프록시 |
| `ops/aws/allstar.env.example` | EC2 운영 환경변수 예시 |
| `ops/aws/duckdns.env.example` | DuckDNS 전용 비밀값 예시 |
| `ops/aws/scripts/bootstrap-ec2.sh` | Docker·Compose·AWS CLI 설치와 systemd 등록 |
| `ops/aws/scripts/allstar-start.sh` | 구성 검증·이미지 빌드·전체 시작·준비 확인 |
| `ops/aws/scripts/allstar-stop.sh` | Prometheus 스냅샷·S3 최종 동기화·전체 종료 |
| `ops/aws/scripts/allstar-deploy.sh` | `main` 최신 커밋 반영과 재배포 |
| `ops/aws/scripts/duckdns-update.sh` | IMDSv2 공인 IPv4로 DuckDNS 갱신 |
| `ops/aws/scripts/s3-sync.sh` | 로그·보고서·백업 변경분 S3 동기화 |
| `ops/aws/systemd/*` | 부팅 자동 시작과 하루 1회 동기화 |

## 3. EC2 생성 시 기준

- Ubuntu Server LTS를 사용한다.
- 인스턴스 메타데이터는 `IMDSv2 only`로 설정한다.
- EC2 IAM 역할을 연결하고 장기 Access Key는 서버에 저장하지 않는다.
- Security Group 인바운드는 다음만 허용한다.

| 포트 | 소스 |
|---:|---|
| `22` | 관리자 현재 공인 IP `/32` |
| `80` | `0.0.0.0/0`, 필요하면 `::/0` |
| `443` | `0.0.0.0/0`, 필요하면 `::/0` |

`3000`, `6001~6006`, `8000`, `8100`, `8200`, `8300`, `8501`, `9090`은 Security Group에 추가하지 않는다.

## 4. S3와 IAM 역할

S3 버킷은 다음을 먼저 설정한다.

- 퍼블릭 액세스 차단
- 버전 관리 `사용`
- 기본 서버 측 암호화 `사용`
- 리전 `ap-northeast-2`

EC2 IAM 역할에는 대상 버킷·접두사에 한해 다음 권한이 필요하다.

- 버킷 목록 확인: `s3:ListBucket`
- 객체 업로드·조회: `s3:PutObject`, `s3:GetObject`
- 멀티파트 업로드 정리: `s3:AbortMultipartUpload`
- GPT 호출: AWS 관리형 정책 `AmazonBedrockMantleInferenceAccess`
- Claude 호출: `bedrock:InvokeModel`

GPT는 `us-west-2`의 Bedrock Mantle Responses API, Claude는 `ap-northeast-2`의 Bedrock Runtime과 글로벌 추론 프로필을 사용한다. Anthropic 최초 사용 양식과 대상 모델 접근을 AWS 계정에서 먼저 완료한다. 환경 파일에는 리전·모델, `S3_BUCKET`, `S3_PREFIX`만 기록한다. AWS Access Key와 Secret Key, OpenAI·Anthropic API 키는 기록하지 않는다.

## 5. EC2 최초 설치

EC2의 SSH 터미널에서 실행한다. 브라우저의 CloudShell이 아니라 **해당 EC2에 접속한 SSH 터미널**이다.

```bash
curl -fsSL \
  https://raw.githubusercontent.com/karlamatstar/ALLSTAR_QA/main/ops/aws/scripts/bootstrap-ec2.sh \
  -o /tmp/bootstrap-ec2.sh
sudo bash /tmp/bootstrap-ec2.sh
```

스크립트는 다음을 수행한다.

1. Docker Engine·Compose 플러그인 설치
2. AWS CLI v2 설치
3. `/opt/allstar`에 `main` 체크아웃
4. `/etc/allstar` 환경 파일 예시 생성
5. systemd 서비스와 일일 타이머 등록

비밀값이 비어 있으므로 설치 직후 서비스는 자동으로 성공 실행되지 않는다. 다음 환경 파일을 먼저 채운다.

```bash
sudo nano /etc/allstar/allstar.env
sudo nano /etc/allstar/duckdns.env
sudo chmod 600 /etc/allstar/allstar.env /etc/allstar/duckdns.env
```

필수 운영값은 다음과 같다.

- `SERVICE_CONTROL_TOKEN`
- `GRAFANA_ADMIN_PASSWORD`
- `S3_BUCKET`
- `DUCKDNS_TOKEN`

모델 호출 설정은 예시 파일의 다음 기본값을 사용하거나 필요할 때만 변경한다.

- `BEDROCK_RUNTIME_REGION=ap-northeast-2`
- `BEDROCK_MANTLE_REGION=us-west-2`
- `AI_CHAT_MODEL=openai.gpt-oss-20b`
- `AI_JUDGE_MODEL=openai.gpt-oss-120b`
- VOC A~D 역할별 GPT·Claude 모델 ID

내부 토큰과 Grafana 암호는 예를 들어 EC2에서 다음처럼 생성한다.

```bash
openssl rand -hex 32
```

생성한 값은 화면 녹화, Git, 보고서, 일반 로그에 노출하지 않는다.

## 6. 시작·상태·종료

### 최초 시작

```bash
sudo systemctl start allstar-duckdns-update.service
sudo systemctl start allstar.service
sudo systemctl start allstar-s3-sync.timer
```

### 상태 확인

```bash
sudo systemctl status allstar.service --no-pager
sudo systemctl status allstar-s3-sync.timer --no-pager
cd /opt/allstar
sudo docker compose \
  --project-name allstar \
  --env-file /etc/allstar/allstar.env \
  -f compose.yml -f compose.aws.yml ps
```

### 로그 확인

```bash
sudo journalctl -u allstar.service -n 100 --no-pager
sudo journalctl -u allstar-duckdns-update.service -n 50 --no-pager
sudo journalctl -u allstar-s3-sync.service -n 100 --no-pager
```

### 안전 종료

```bash
sudo systemctl stop allstar.service
```

안전 종료는 다음 순서로 동작한다.

1. Prometheus 스냅샷 생성
2. 압축본과 SHA-256 체크섬 생성
3. 로그·보고서·스냅샷을 S3에 최종 동기화
4. AllStar Compose 컨테이너 종료

S3 최종 동기화 오류가 표시되면 EC2를 끄기 전에 원인을 확인하고 다음을 수동 실행한다.

```bash
sudo /opt/allstar/ops/aws/scripts/s3-sync.sh manual
```

## 7. 코드 갱신

로컬에서 `main`을 푸시한 뒤 EC2에서 다음을 실행한다.

```bash
sudo /opt/allstar/ops/aws/scripts/allstar-deploy.sh
```

스크립트는 현재 브랜치와 미커밋 변경 여부를 검사하고 `git pull --ff-only` 후 다시 빌드·시작한다. EC2 작업 폴더에 직접 코드를 수정하지 않는다.

## 8. DuckDNS와 HTTPS

`duckdns-update.sh`는 EC2 IMDSv2 세션 토큰을 발급받고 현재 공인 IPv4를 조회한다. DuckDNS 토큰은 `curl` 명령행 인수나 로그에 출력하지 않는다.

DuckDNS 갱신 API는 GET 요청으로 호출한다. 토큰이 프로세스 목록에 노출되지 않도록 URL 인수에 직접 넣지 않고 표준 입력으로 전달하는 `curl --config -` 방식을 사용한다. 2026-07-25 실제 EC2 최초 검증에서 POST 요청이 HTTP `405`로 거부되는 문제를 확인해 GET 방식으로 수정했다.

갱신 요청은 제한된 3회까지만 재시도하고, `allstar.service`는 DNS 조회 결과가 현재 EC2 공인 IPv4와 일치한 뒤에만 시작한다. 60초 안에 일치하지 않으면 시작을 실패 처리해 잘못된 주소로 인증서 발급을 시도하지 않는다.

Caddy가 공개 인증서를 정상 발급하려면 다음 조건이 필요하다.

- `allstarqa.duckdns.org`가 현재 EC2 공인 IPv4를 가리킴
- Security Group과 OS에서 `80`·`443` 허용
- 다른 프로그램이 호스트 `80`·`443`을 사용하지 않음
- Caddy `/data`가 `/opt/allstar-data/caddy/data`에 영구 저장됨

접속 주소는 다음 두 개다.

- `https://allstarqa.duckdns.org/`
- `https://allstarqa.duckdns.org/grafana/`

## 9. S3 일일 동기화

`allstar-s3-sync.timer`는 하루 한 번 실행하고 `Persistent=true`로 EC2가 꺼져 있던 시각의 실행을 다음 부팅 후 보완한다. `allstar-s3-sync.service`도 부팅 시 한 번 실행한다.

동기화 대상:

- `/opt/allstar-data/output/logs`
- `/opt/allstar-data/output/reports`
- `/opt/allstar-data/output/archives`
- `/opt/allstar-data/prometheus-backups`

`aws s3 sync`는 크기·수정 시간이 같은 파일을 다시 올리지 않는다. `--delete`를 사용하지 않으므로 EC2에서 파일이 정리돼도 S3 객체를 자동 삭제하지 않는다. S3 버전 관리가 켜져 있으므로 같은 키가 바뀌면 이전 버전도 남는다. `.env` 파일은 제외한다.

## 10. `service-control` 내부 인증

Streamlit은 상태 확인·시작·중단 요청에 `X-AllStar-Service-Token` 헤더를 추가한다. 브리지는 토큰이 없거나 틀리면 HTTP `401`, 토큰 자체가 설정되지 않았으면 HTTP `503`을 반환한다.

- 토큰은 `SERVICE_CONTROL_TOKEN` 환경변수로만 전달한다.
- 토큰 값은 제어 로그와 오류 응답에 기록하지 않는다.
- `service-control` 호스트 포트는 공개하지 않는다.
- Docker 소켓은 `service-control` 하나에만 연결한다.
- 제어 가능 서비스는 `portfolio-api`, `voc-api`로 고정한다.

화면의 `1234`는 시연용 실행 잠금이고 이 내부 토큰과 목적이 다르다.

## 11. 2026-07-25 로컬 Docker 검증

조건:

- Windows Docker Desktop Engine `29.6.1`
- Docker Compose `v5.3.0`
- 외부 AI API 호출 없음
- 공개 운영 비밀값 대신 검증용 더미값 사용
- 로컬 Caddy 주소 `http://localhost:18080`

결과:

- AWS Compose 합성 검사 성공
- 사용자 정의 이미지 전체 빌드 성공
- Caddy 포함 전체 `14개` 컨테이너 실행 성공
- 대시보드 Caddy 경유 HTTP `200`
- Grafana `/grafana/` Caddy 경유 HTTP `200`
- 호스트 공개 포트는 Caddy 검증 포트 `18080`, `18443`만 존재
- AI·VOC·Streamlit·K6·Prometheus·Grafana·`service-control` 직접 호스트 포트 미공개
- 내부 토큰 미입력 `401`, 오답 `401`, 정상 토큰 `200`
- Prometheus 관리자 스냅샷 API 성공
- 관련 자동검사 `20개` 통과
- 전체 비API 회귀 `298개 통과·3개 환경 제외·2개 선택 제외`

이 절은 실제 AWS 비용이 발생하지 않는 로컬 사전 검증 결과다. 실제 AWS 종단 결과는 다음 절에 별도로 기록한다.

## 12. 2026-07-25 실제 EC2 최초 배포 검증

조건:

- 리전: `ap-northeast-2`
- Ubuntu Server `26.04 LTS`, x86_64
- 인스턴스: `c7i-flex.large`(2 vCPU, 4 GiB)
- EBS: gp3 `30 GiB`
- IAM 인스턴스 프로파일: `AllStarEC2S3Role`
- S3 버킷: `allstarqa-portfolio-karl9star-20260725`
- 공개 도메인: `allstarqa.duckdns.org`

결과:

- EC2 상태 검사 `3/3` 통과
- `bootstrap-ec2.sh`로 Docker Engine·Compose·AWS CLI 설치와 `main` 체크아웃 성공
- 최초 DuckDNS POST 요청의 HTTP `405` 원인을 확인하고 GET 방식으로 수정
- IMDSv2 공인 IPv4 기반 DuckDNS 갱신 성공
- Caddy 포함 전체 `14개` 컨테이너 실행과 내부 준비 검사 성공
- `https://allstarqa.duckdns.org/` HTTPS `200`, 인증서 검증 성공
- `https://allstarqa.duckdns.org/grafana/` HTTPS `200`, 공개 Grafana 조회 성공
- EC2 IAM 역할로 신규 S3 버킷 접근과 실제 검증 로그 업로드 성공
- S3 버전 관리 활성화, SSE-S3 기본 암호화, 모든 퍼블릭 액세스 차단 확인
- 일일 S3 동기화 타이머 활성화
- 최초 빌드 후 루트 파일 시스템 약 `11 GiB` 사용, 약 `18 GiB` 여유

아직 별도로 확인할 항목:

- EC2 중지·재시작 후 systemd 자동 복구
- Prometheus 시계열과 Grafana 설정의 재시작 전후 보존
- 시연용 AI·VOC 테스트케이스 각 3건의 실제 AWS 실행

### 장애·기능 검증 K6 Runner 보완

최초 공개 배포 후 대시보드에서 장애·기능 검증을 실행했을 때 K6 장애
재현 6건은 모두 통과했다. 이어지는 비API Pytest는 K6 Runner 이미지에
`compose.aws.yml`과 `.env.example`이 없어서 수집 오류로 중단됐다.

K6 Runner Dockerfile에 두 공개 설정 파일을 추가해 AWS 배포 정책 검사와
테스트 탭 암호 설정 검사가 컨테이너에서도 동작하도록 보완한다. 실제
비밀값이 들어 있는 `.env`는 계속 Docker 빌드 컨텍스트에서 제외한다.

보완 이미지를 실제 EC2에서 다시 실행해 비API 회귀 `298개 통과·2개 환경
제외·2개 선택 제외`를 확인했다. 이어 새 EBS에는 정식 장애 보고서 폴더가
아직 없다는 점이 드러나 보고서 생성 전에
`_OUTPUT/reports/defects/chaos`를 자동 생성하도록 추가 보완했다.

최종 재검증:

- 실행일: 2026-07-25
- 실행 ID: `20260725_145035_aabeea2f`
- 조건: AWS K6 Runner, 외부 AI API 호출 제외
- K6 장애 재현: 6건 모두 통과
- 비API 회귀: `300 passed, 2 skipped, 2 deselected`
- 종료 상태: `completed`, 종료 코드 `0`
- EBS 산출물: 실행 로그, K6 JSON, 결함 Markdown·Word, QA 최신 요약과 manifest
- S3 산출물: 위 로그·보고서·manifest 수동 동기화 및 AES256 암호화 확인

같은 날 사용자가 실행한 기본 동작·무작위 요청 시험은 설계대로 누적 로그와
K6 JSON만 생성됐고, 서버 연결 성능 종합 시험은 누적 로그와 성능 정식
보고서·QA 최신 요약·manifest가 생성됐다. 실패했던 최초 장애·기능 검증은
원문 로그만 보존하고 정식 보고서를 덮어쓰지 않았으며, 보완 후 정상 실행이
정식 보고서를 생성했다.

## 관련 문서

- `AWS_PUBLIC_ACCESS_AND_EXECUTION_GUARD_PLAN.md`
- `AWS_REVERSIBLE_DEPLOYMENT_AND_LOCAL_RESTORE.md`
- `CHAT_SERVICE_CONTROL_BRIDGE.md`
- `DOCKER_STREAMLIT_K6_RUNNER.md`
