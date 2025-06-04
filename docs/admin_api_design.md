# 관리자 페이지 API 시스템 설계서

## 1. 개요

관리자가 에러가 발생한 파싱룰을 조회, 수정, 테스트, 재전송할 수 있는 API 시스템을 구축합니다.

## 2. 시스템 아키텍처

### 2.1 SOLID 원칙 적용
- **SRP (Single Responsibility)**: 각 API 엔드포인트는 하나의 기능만 담당
- **OCP (Open/Closed)**: 새로운 기능 추가 시 기존 코드 수정 최소화
- **LSP (Liskov Substitution)**: 인터페이스 구현체 교체 가능
- **ISP (Interface Segregation)**: 필요한 메서드만 포함하는 인터페이스
- **DIP (Dependency Inversion)**: 추상화에 의존, 구체적 구현에 의존하지 않음

### 2.2 KISS 원칙 적용
- 간단하고 명확한 API 구조
- 직관적인 URL 패턴
- 최소한의 복잡성으로 기능 구현

## 3. 데이터베이스 설계

### 3.1 PostgreSQL 마이그레이션
```sql
-- parsing_errors 테이블: 에러 발생 파싱룰 정보
CREATE TABLE parsing_errors (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(10) NOT NULL,
    raw_data TEXT NOT NULL,
    receipt_data JSONB,
    error_message TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'ERROR',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- parsing_rules 테이블: 파싱룰 정보
CREATE TABLE parsing_rules (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(10) NOT NULL,
    rule_type VARCHAR(50) NOT NULL,
    xml_content TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ml_training_data 테이블: 머신러닝 학습용 데이터
CREATE TABLE ml_training_data (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(10) NOT NULL,
    receipt_data JSONB NOT NULL,
    xml_result TEXT NOT NULL,
    parsing_error_id INTEGER REFERENCES parsing_errors(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_parsing_errors_client_id ON parsing_errors(client_id);
CREATE INDEX idx_parsing_errors_status ON parsing_errors(status);
CREATE INDEX idx_parsing_rules_client_id ON parsing_rules(client_id);
CREATE INDEX idx_ml_training_data_client_id ON ml_training_data(client_id);
```

## 4. API 설계

### 4.1 에러 파싱룰 조회 API
```
GET /api/admin/parsing-errors
Query Parameters:
- client_id: string (optional)
- status: string (optional) [ERROR, FIXED, TESTING]
- page: int (default: 1)
- limit: int (default: 20)

Response:
{
    "data": [
        {
            "id": 1,
            "client_id": "CLIENT1",
            "receipt_data": {...},
            "error_message": "파싱 실패",
            "status": "ERROR",
            "created_at": "2024-01-01T10:00:00Z"
        }
    ],
    "total": 100,
    "page": 1,
    "limit": 20
}
```

### 4.2 특정 에러 상세 조회 API
```
GET /api/admin/parsing-errors/{error_id}

Response:
{
    "id": 1,
    "client_id": "CLIENT1",
    "raw_data": "...",
    "receipt_data": {...},
    "error_message": "파싱 실패",
    "status": "ERROR",
    "created_at": "2024-01-01T10:00:00Z"
}
```

### 4.3 파싱룰 수정 API
```
PUT /api/admin/parsing-errors/{error_id}/rule
Request Body:
{
    "xml_content": "<PARSER>...</PARSER>"
}

Response:
{
    "success": true,
    "message": "파싱룰이 수정되었습니다."
}
```

### 4.4 파싱룰 테스트 API
```
POST /api/admin/parsing-errors/{error_id}/test
Request Body:
{
    "xml_content": "<PARSER>...</PARSER>"
}

Response:
{
    "success": true,
    "result": {...},
    "is_valid": true
}
```

### 4.5 수정된 파싱룰 전송 API
```
POST /api/admin/parsing-errors/{error_id}/submit
Request Body:
{
    "xml_content": "<PARSER>...</PARSER>"
}

Response:
{
    "success": true,
    "message": "파싱룰이 전송되었습니다.",
    "rule_id": 123
}
```

## 5. 서비스 레이어 구조

```
aiagent/
├── api/
│   ├── __init__.py
│   ├── dependencies.py      # 의존성 주입
│   └── v1/
│       ├── __init__.py
│       └── admin/
│           ├── __init__.py
│           ├── parsing_errors.py
│           └── schemas.py
├── services/
│   ├── __init__.py
│   ├── admin_service.py     # 관리자 기능 서비스
│   └── ml_data_service.py   # ML 데이터 서비스
├── repositories/
│   ├── __init__.py
│   ├── parsing_error_repository.py
│   ├── parsing_rule_repository.py
│   └── ml_training_data_repository.py
└── models/
    ├── __init__.py
    ├── parsing_error.py
    ├── parsing_rule.py
    └── ml_training_data.py
```

## 6. 주요 컴포넌트

### 6.1 Repository Pattern
- 데이터베이스 액세스 로직 분리
- 테스트 가능한 구조
- 의존성 역전 원칙 적용

### 6.2 Service Layer
- 비즈니스 로직 캡슐화
- 트랜잭션 관리
- 도메인 로직 집중

### 6.3 API Layer
- HTTP 요청/응답 처리
- 입력 검증
- 인증/권한 처리

## 7. 에러 처리 및 로깅

- 구조화된 에러 응답
- 상세 로깅 (요청/응답, 에러 정보)
- 모니터링 메트릭

## 8. 보안 고려사항

- API 키 기반 인증
- 입력 데이터 검증
- SQL 인젝션 방지
- XSS 방지 