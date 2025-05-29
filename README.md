# SmartCast AI Agent

스마트 영수증 파싱을 위한 AI 에이전트 시스템입니다. GPT-4를 활용하여 영수증 데이터를 자동으로 분석하고 파싱 규칙을 생성합니다.

## 🚀 주요 기능

- **AI 파싱 규칙 생성**: GPT-4를 사용한 자동 영수증 파싱 규칙 생성
- **규칙 병합**: 기존 규칙과 새로운 데이터를 지능적으로 병합
- **실시간 처리**: ZeroMQ 기반 실시간 메시지 처리
- **데이터베이스 연동**: SQLAlchemy를 통한 결과 저장 및 관리
- **Docker 지원**: 컨테이너 기반 배포 지원

## 📋 시스템 요구사항

- Python 3.11+
- Docker & Docker Compose
- OpenAI API Key

## 🛠️ 설치 및 실행

### 1. 저장소 클론
```bash
git clone https://github.com/younggyun4242/smartcast-aiagent.git
cd smartcast-aiagent
```

### 2. 환경 변수 설정
```bash
# .env 파일 생성
cp .env.example .env

# OpenAI API 키 설정
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Docker Compose 실행
```bash
docker-compose up -d
```

### 4. 개발 환경 설정 (선택사항)
```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

## 🏗️ 프로젝트 구조

```
smartcast-aiagent/
├── aiagent/                    # 메인 애플리케이션
│   ├── api/                   # API 엔드포인트
│   ├── core/                  # 핵심 로직 (브로커, 프로토콜)
│   ├── db/                    # 데이터베이스 모델 및 연결
│   ├── prompts/               # AI 프롬프트 템플릿
│   ├── services/              # 비즈니스 로직 (파서, 프로세서)
│   └── utils/                 # 유틸리티 (로거, 이메일)
├── docker-compose.yml         # Docker Compose 설정
├── Dockerfile                 # 메인 애플리케이션 Dockerfile
├── Dockerfile.broker          # 브로커 Dockerfile
├── requirements.txt           # Python 의존성
├── brokerserver.py           # ZeroMQ 브로커 서버
└── test_parser.py            # 파서 테스트 스크립트
```

## 🔧 API 사용법

### AI 파싱 규칙 생성
```python
# AI_GENERATE 요청
{
    "type": "xml",
    "mode": "GENERATE", 
    "client_id": "CLIENT01",
    "transaction_id": "uuid-here",
    "receipt_data": {
        "raw_data": "hex_encoded_receipt_data"
    }
}
```

### 기존 규칙과 병합
```python
# AI_MERGE 요청
{
    "type": "xml",
    "mode": "MERGE",
    "client_id": "CLIENT01", 
    "transaction_id": "uuid-here",
    "receipt_data": {
        "raw_data": "hex_encoded_receipt_data"
    },
    "current_xml": "existing_parsing_rules",
    "current_version": "CLIENT01_001.xml"
}
```

## 🚦 테스트

```bash
# 파서 테스트 실행
python test_parser.py

# 특정 테스트만 실행
python test_parser.py --generate  # AI_GENERATE 테스트
python test_parser.py --merge     # AI_MERGE 테스트
```

## 📊 모니터링

- **로그**: `logs/` 디렉토리에서 애플리케이션 로그 확인
- **데이터베이스**: SQLite DB를 통한 처리 결과 추적
- **메트릭스**: API를 통한 시스템 메트릭스 확인

## 🔒 보안

- API 키는 환경 변수로 관리
- 민감한 데이터는 .gitignore로 제외
- Docker 시크릿 지원

## 🤝 기여하기

1. 이 저장소를 포크합니다
2. 기능 브랜치를 생성합니다 (`git checkout -b feature/AmazingFeature`)
3. 변경사항을 커밋합니다 (`git commit -m 'Add some AmazingFeature'`)
4. 브랜치에 푸시합니다 (`git push origin feature/AmazingFeature`)
5. Pull Request를 생성합니다

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 📞 문의

프로젝트에 대한 질문이 있으시면 이슈를 생성해 주세요.

---

**Note**: 이 프로젝트는 영수증 데이터 처리를 위한 AI 시스템입니다. 상용 환경에서 사용하기 전에 충분한 테스트를 수행하시기 바랍니다. 