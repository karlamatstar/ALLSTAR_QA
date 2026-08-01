# AI Agent QA AllStar

AWS에 배포한 AI 에이전트·VOC 멀티 에이전트 통합 QA 시스템입니다. 웹 브라우저에서 [ALLSTAR QA 대시보드](https://allstarqa.duckdns.org/)에 접속하면 실시간 대화, 품질평가, 테스트케이스, 부하·장애 시험, Grafana 모니터링과 자동 보고서를 한 화면에서 실행하고 확인할 수 있습니다.

이 프로젝트는 장애가 없는 결과만 PASS로 보여주기 위한 서비스가 아닙니다. 정상 상태와 함께 의도적으로 설계한 결함·제한·서버 중단 시나리오를 재현해 FAIL과 N/A가 어떻게 탐지·기록·복구되는지 확인하는 QA 실습 프로젝트입니다. 미완성 상태를 방치한 것이 아니라, 품질검사가 실제 문제를 찾아내는 과정을 관찰할 수 있도록 시험 가능한 장애 조건을 통제해 구성했습니다.

## 접속 주소

| 화면 | 공개 주소 | 용도 |
|---|---|---|
| 통합 대시보드 | [https://allstarqa.duckdns.org/](https://allstarqa.duckdns.org/) | 모든 대화·시험·보고서·모니터링 기능 |
| Grafana | [https://allstarqa.duckdns.org/grafana/](https://allstarqa.duckdns.org/grafana/) | 운영 지표 상세 조회 |

EC2가 실행 중이면 별도 프로그램 설치 없이 브라우저만으로 이용합니다. AI·VOC API, 6개 VOC gRPC 에이전트, K6 Runner, Prometheus와 Grafana는 외부 포트로 직접 공개하지 않고 HTTPS 프록시 뒤의 내부 Docker 네트워크에서 동작합니다.

## 대시보드 기능

대시보드는 다음 7개 상위 메뉴로 구성됩니다.

| 구분 | 메뉴 | 주요 기능 |
|---|---|---|
| 운영 | AI 에이전트 챗봇 | 교육과정 질문, API·규칙 기반 답변 비교, 독립 품질평가 |
| 운영 | VOC 챗봇 | A~D 모델 프로필, 7단계 처리, 9항목·100점 채점 |
| 운영 | 모니터링 | AI·VOC·K6·QA Grafana 대시보드 4종 |
| 운영 | 보고서 모음 | 실시간·테스트케이스·성능·장애 최신 보고서 |
| 시험 | K6 부하 테스트 | 기본·부하·무작위·한계·급증·장애·실제 API 성능 시험 |
| 시험 | AI 에이전트 테스트케이스 | 사례 관리, 전체 실행, 배치 품질 비교, 상세 결과 |
| 시험 | VOC 테스트케이스 | 사례 관리, A~D 프로필별 전체 실행, 단계별 결과 |

### AI 에이전트 챗봇

- 서버 연결 방식(API)과 로컬 규칙 기반 답변을 같은 질문으로 비교합니다.
- 답변 생성 뒤 두 결과를 각각 독립 평가하고 대화 로그·품질 현황·보고서를 자동 갱신합니다.
- 질문과 답변의 언어를 일치시킵니다. 한국어 질문의 일반 답변·거절·오류 안내는 한국어로 처리합니다.
- `503`, `504`, 실제 채팅 서버 중단 시험으로 장애 감지와 재접속을 확인합니다.
- 장애 시험은 외부 AI를 호출하지 않으며 품질 FAIL과 구분해 N/A로 기록합니다.

### VOC 챗봇

질문마다 A~D 모델 프로필을 선택하고 다음 7단계를 확인합니다.

1. Interpreter 질문 의도 분석
2. Retriever 관련 의견 검색
3. Summarizer 내용 요약
4. Evaluator 초기 품질평가
5. Critic 결과 검토
6. Improver 최종 개선안 생성
7. 독립 LLM Judge 품질평가

최종 결과는 Interpreter 해석 정확성, 검색 관련성, 요약 사실성·요약성, 평가 타당성, 비평 탐지력, 개선안 실행 가능성, 에이전트 연계 품질, 장애 대응·로그, 성능을 합산한 9항목·100점 기준으로 기록합니다.

### K6 부하·장애 시험

대시보드 카드에서 가상 사용자와 실행 시간을 설정하고 다음 시험을 실행합니다.

- 기본 동작, 일반 부하, 무작위 요청, 한계 부하, 순간 급증
- 장애·기능 검증
- 실제 AI API를 단계별로 호출하는 서버 연결 성능 종합 시험

실행 중에는 고정 높이 터미널, 진행 상태와 중지 버튼을 표시합니다. 직접 부하 5종은 Prometheus·Grafana 지표를 남기고, 장애·기능 검증과 실제 API 성능 시험은 정식 보고서도 생성합니다.

### 테스트케이스 관리와 실행 보호

- AI·VOC 테스트케이스는 각각 최소 1개, 최대 10개까지 관리합니다.
- 한 번에 실행하는 범위도 최대 10개이며, 10개가 등록되면 추가 버튼이 잠깁니다.
- 테스트케이스가 1개만 남으면 삭제할 수 없습니다.
- 외부 AI 호출 가능성을 확인하는 필수 체크 뒤 실행 비밀번호를 입력하고 `확인` 버튼 또는 Enter를 눌러야 실행 버튼이 활성화됩니다.
- 필수 체크를 해제했다가 다시 선택하면 비밀번호를 다시 확인해야 합니다.
- VOC 프로필 실행이 끝나 `완료 확인 대기` 상태가 되면 A~D 선택과 전체 실행 버튼을 모두 잠급니다. `완료 상태 닫기·다음 테스트 준비`를 눌러야 다음 실행이 가능합니다.

실행 비밀번호는 강한 사용자 인증이 아니라 공개 화면에서 비용·부하·장애 기능이 실수로 실행되는 것을 줄이는 세션별 안전장치입니다.

## 모델 구성

모든 생성·평가 모델은 외부 제공자의 장기 API 키 대신 EC2 IAM 역할과 Amazon Bedrock을 통해 호출합니다.

| 기능 | 모델 | AWS 호출 경로 |
|---|---|---|
| AI 에이전트 답변 생성 | OpenAI `gpt-oss-20b` | Bedrock Mantle, `us-west-2` |
| AI 에이전트 독립 평가 | OpenAI `gpt-oss-120b` | Bedrock Mantle, `us-west-2` |
| VOC OpenAI 계열 생성 | OpenAI `gpt-oss-20b` | Bedrock Mantle, `us-west-2` |
| VOC OpenAI 계열 평가 | OpenAI `gpt-oss-120b` | Bedrock Mantle, `us-west-2` |
| VOC Anthropic 계열 생성·평가 | Claude Haiku 4.5 | Bedrock Runtime 글로벌 추론 프로필, `ap-northeast-2` |

### VOC A~D 프로필

| 프로필 | 답변 생성 | 독립 평가 | 비교 목적 |
|---|---|---|---|
| A | `gpt-oss-20b` | Claude Haiku 4.5 | 기본 권장 교차 평가 |
| B | Claude Haiku 4.5 | `gpt-oss-120b` | 역방향 교차 평가 |
| C | `gpt-oss-20b` | `gpt-oss-120b` | OpenAI 계열 내 역할 분리 |
| D | Claude Haiku 4.5 | Claude Haiku 4.5 | Anthropic 단일 계열 기준 비교 |

생성 모델과 Judge 모델은 독립적으로 기록합니다. 모델 호출에 실패하면 품질 FAIL로 왜곡하지 않고 평가 불가 N/A로 보존합니다. 질문 언어와 답변 언어가 어긋나는 경우에는 안전한 거절이어도 필수 규칙 위반으로 처리합니다.

## PASS·FAIL 해석

품질평가는 단순히 모든 결과를 PASS로 만드는 것이 목적이 아닙니다.

- `PASS`: 정의된 품질 기준을 충족한 정상 결과
- `REVIEW`: 사용할 수 있으나 사람의 확인이나 개선이 필요한 결과
- `FAIL`: 품질 기준 미달 또는 필수 규칙 위반
- `N/A`: 서버·네트워크·모델 호출 장애로 품질 자체를 채점할 수 없는 결과

핵심 키워드 문구 불일치처럼 비차단 규칙이 FAIL이어도 독립 평가가 PASS 기준을 충족할 수 있습니다. 이 경우 자동 보고서는 실제 규칙 실패 원인, 비차단 여부, 독립 평가 점수와 PASS 기준을 함께 설명합니다. 반면 안전성이나 질문·답변 언어 불일치 같은 필수 규칙 위반은 종합 PASS로 유지하지 않습니다.

## 자동 보고서와 모니터링

대시보드의 `보고서 모음`에서 다음 최신 결과를 확인합니다.

1. AI 에이전트 실시간 대화 보고서
2. AI 에이전트 테스트케이스 보고서
3. VOC 실시간 대화 보고서
4. VOC A~D 테스트케이스·종합 비교 보고서
5. 서버 연결 성능 보고서
6. 장애·기능 검증 보고서

챗봇 보고서는 채점 완료 후 자동 갱신됩니다. 테스트케이스 최신 정식 보고서는 등록된 전체 범위가 정상 완료된 경우에만 교체하고, 중단·API 실패 때 확보한 원문 로그는 보존하되 이전 정상 보고서를 덮어쓰지 않습니다. 비교 그래프는 모델·프로필마다 서로 다른 색상 계열, 선 모양과 마커를 사용해 겹치는 결과도 구분할 수 있게 합니다.

Grafana에서는 요청 수, 오류율, 응답시간, Judge 판정·점수·처리시간, VOC 7단계별 평균·p95 시간, 실패 원인, K6 부하 지표와 A~D 테스트케이스 결과를 확인합니다.

## AWS 배포 구조

```text
사용자 브라우저
  └─ HTTPS · allstarqa.duckdns.org
      └─ Caddy
          ├─ /          → Streamlit 통합 대시보드
          └─ /grafana/  → Grafana

EC2 Docker 내부 네트워크
  ├─ AI API · VOC API · VOC gRPC 에이전트 6개
  ├─ K6 Runner · service-control
  ├─ Prometheus · Grafana
  └─ Streamlit · Caddy

영구 데이터
  ├─ EC2 EBS /opt/allstar-data
  └─ S3 변경분 백업
```

- 외부 공개 포트는 Caddy의 `80`, `443`만 사용합니다.
- 애플리케이션 API, Streamlit 원본 포트, Grafana 원본 포트와 에이전트 포트는 인터넷에 공개하지 않습니다.
- Caddy가 HTTPS 인증서 발급과 갱신을 담당합니다.
- DuckDNS는 EC2의 현재 공인 IPv4를 갱신합니다.
- systemd가 부팅 시 서비스를 시작하고 종료 전 로그·보고서를 S3에 동기화합니다.
- AWS Access Key, Bedrock 외부 API 키, DuckDNS 토큰, Grafana 암호와 내부 서비스 토큰은 Git에 저장하지 않습니다.

운영 배포 절차는 [`_DOCS/AWS_EC2_DOCKER_DEPLOYMENT_RUNBOOK.md`](_DOCS/AWS_EC2_DOCKER_DEPLOYMENT_RUNBOOK.md), 공개 범위와 실행 보호 기준은 [`_DOCS/AWS_PUBLIC_ACCESS_AND_EXECUTION_GUARD_PLAN.md`](_DOCS/AWS_PUBLIC_ACCESS_AND_EXECUTION_GUARD_PLAN.md)를 따릅니다.

## 저장 데이터

- 원본 로그: `_OUTPUT/logs/`
- 최신·이력 보고서: `_OUTPUT/reports/`
- 보고서 연결 정보: `_OUTPUT/reports/manifests/`
- 서비스 로그: `_OUTPUT/logs/services/`

AI·VOC 실시간 로그는 한국 날짜 기준으로 누적합니다. 최근 활동 날짜와 정상 완료 실행은 원본으로 유지하고 오래된 원본은 검증 뒤 GZIP으로 압축합니다. 최신 보고서·그래프·manifest와 현재 진행 로그는 압축하지 않으며, 대시보드는 원본과 압축 로그를 함께 읽습니다.

## 저장소 구성

| 경로 | 내용 |
|---|---|
| `src/allstar/` | AI·VOC·공통 서비스와 Streamlit 대시보드 |
| `ops/` | Docker, AWS, Caddy, Prometheus, Grafana, K6 구성 |
| `tools/` | 배포·QA·관리 실행 도구 |
| `tests/` | 비과금 회귀검사와 승인형 실제 Bedrock 검사 |
| `_OUTPUT/` | 실행 로그·보고서·그래프·manifest |
| `_DOCS/` | 설계·운영·검증 상세 문서 |

## 검증 원칙

- 기본 자동검사는 외부 AI 호출 없이 실행합니다.
- 실제 Bedrock 검사는 권한과 비용을 확인한 AWS 환경에서 대표 사례만 제한적으로 실행합니다.
- 장애 시험과 실제 품질 실패를 분리하고, 사용할 수 없는 Judge 결과는 N/A로 남깁니다.
- 코드와 대시보드 문구에 표시하는 모델명은 실제 실행 설정에서 가져옵니다.
- 비밀값은 커밋·이미지·보고서·오류 메시지에 남기지 않습니다.

전체 구현·검증 상태는 [`_DOCS/PROJECT_PROGRESS_CHECKLIST.md`](_DOCS/PROJECT_PROGRESS_CHECKLIST.md), 문서 목록은 [`_DOCS/README.md`](_DOCS/README.md)에서 확인할 수 있습니다.
