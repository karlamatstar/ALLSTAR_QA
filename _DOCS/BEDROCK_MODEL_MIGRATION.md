# Amazon Bedrock 모델 전환 범위

## 적용 원칙

OpenAI와 Anthropic에 직접 연결하던 장기 API 키를 폐기하고 AWS 기본 자격 증명 체인으로 통합한다. 운영 EC2에서는 인스턴스에 연결된 IAM 역할을 사용하며 소스 코드와 환경 파일에 AWS Access Key, Secret Key, OpenAI API 키, Anthropic API 키를 저장하지 않는다.

## 호출 경로

| 기능 | 모델 | AWS 경로 | 리전 |
|---|---|---|---|
| 일반 교육과정 챗봇 답변 | GPT-5.6 Luna | Bedrock Mantle Responses API | `us-west-2` |
| 일반 챗봇 독립 채점 | GPT-5.6 Terra | Bedrock Mantle Responses API | `us-west-2` |
| VOC OpenAI 계열 생성 | GPT-5.6 Luna | Bedrock Mantle Responses API | `us-west-2` |
| VOC OpenAI 계열 Judge | GPT-5.6 Terra | Bedrock Mantle Responses API | `us-west-2` |
| VOC Anthropic 계열 생성 | Claude Sonnet 4.6 | Bedrock Runtime InvokeModel | `ap-northeast-2` |
| VOC Anthropic 계열 Judge | Claude Sonnet 5 | Bedrock Runtime InvokeModel | `ap-northeast-2` |

VOC A/B/C/D의 생성·독립 평가 조합은 그대로 유지한다. 제공자와 모델 표기도 기존 보고서 의미를 보존하고, 전송 계층만 공통 Bedrock 어댑터로 바꾼다.

## 성능 테스트 적용

`ops/performance/api_latency_test.js`는 실제 `/chat`을 호출하므로 GPT-5.6 Luna의 Bedrock Mantle 왕복시간과 애플리케이션 처리시간을 함께 측정한다. 1명·10명·25명 단계는 각각 독립 실행되며 결과 태그에 `amazon-bedrock`과 모델 ID를 남긴다.

대량 부하·랜덤·스트레스·스파이크·운영 안정성 시험은 `/chat_mock`을 유지한다. 이 시험의 목적은 Docker·FastAPI·네트워크·모니터링 처리량 검증이며, 실제 모델을 대량 호출하면 토큰 비용·외부 쿼터·모델 변동성이 서버 성능 결과를 왜곡하기 때문이다.

## 배포 전 확인

1. EC2 IAM 역할에 `AmazonBedrockMantleInferenceAccess`와 `bedrock:InvokeModel` 권한을 부여한다.
2. AWS 계정에서 Anthropic 최초 사용 양식과 사용할 Claude 모델 접근을 완료한다.
3. EC2 인스턴스 메타데이터 옵션의 응답 홉 제한이 Docker 컨테이너에서 IAM 역할 자격 증명을 읽을 수 있게 설정됐는지 확인한다.
4. `aws sts get-caller-identity`가 EC2 역할을 반환하는지 확인한다.
5. 챗봇 1건과 VOC 대표 1건만 호출해 두 리전의 모델 접근·응답 파싱을 확인한 뒤 성능 시험 범위를 늘린다.

실제 모델을 사용하는 pytest는 승인된 AWS 환경에서 `RUN_LIVE_BEDROCK_TESTS=1`을 설정했을 때만 실행한다. 기본 회귀검사는 모델 호출 없이 어댑터의 요청 형식과 애플리케이션 동작을 검증한다.

실제 모델 호출은 AWS 권한과 과금이 발생하므로 이 로컬 정리 단계에서는 수행하지 않는다.
