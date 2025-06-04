-- 관리자 페이지 API용 PostgreSQL 스키마 생성 스크립트

-- 기존 테이블이 있다면 삭제 (개발 환경용)
DROP TABLE IF EXISTS ml_training_data CASCADE;
DROP TABLE IF EXISTS parsing_rules CASCADE;
DROP TABLE IF EXISTS parsing_errors CASCADE;

-- 영수증 처리 기록 테이블 (기존 기능)
CREATE TABLE IF NOT EXISTS receipt_records (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(50) NOT NULL,
    transaction_id VARCHAR(100) NOT NULL UNIQUE,
    raw_data TEXT NOT NULL,
    parser_xml TEXT,
    xml_result TEXT,
    is_valid BOOLEAN DEFAULT FALSE,
    error_message VARCHAR(500) NOT NULL DEFAULT '',
    processing_time REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- parsing_errors 테이블: 에러 발생 파싱룰 정보
CREATE TABLE parsing_errors (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(50) NOT NULL,
    transaction_id VARCHAR(100) NOT NULL,
    receipt_data JSONB NOT NULL,
    error_message TEXT NOT NULL,
    error_type VARCHAR(50) NOT NULL DEFAULT 'PARSING_ERROR',
    status VARCHAR(20) NOT NULL DEFAULT 'ERROR',
    retry_count INTEGER DEFAULT 0,
    last_retry_at TIMESTAMP,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- parsing_rules 테이블: 파싱룰 정보
CREATE TABLE parsing_rules (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(50) NOT NULL,
    rule_name VARCHAR(100) NOT NULL,
    rule_type VARCHAR(50) NOT NULL DEFAULT 'GENERAL',
    xml_content TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    description TEXT,
    created_by VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ml_training_data 테이블: 머신러닝 학습용 데이터
CREATE TABLE ml_training_data (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(50) NOT NULL,
    parsing_error_id INTEGER REFERENCES parsing_errors(id),
    receipt_data JSONB NOT NULL,
    xml_result TEXT NOT NULL,
    validation_status VARCHAR(20) DEFAULT 'PENDING',
    data_quality_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 생성
CREATE INDEX idx_receipt_records_client_id ON receipt_records(client_id);
CREATE INDEX idx_receipt_records_transaction_id ON receipt_records(transaction_id);
CREATE INDEX idx_receipt_records_created_at ON receipt_records(created_at);

CREATE INDEX idx_parsing_errors_client_id ON parsing_errors(client_id);
CREATE INDEX idx_parsing_errors_status ON parsing_errors(status);
CREATE INDEX idx_parsing_errors_created_at ON parsing_errors(created_at);
CREATE INDEX idx_parsing_errors_client_status ON parsing_errors(client_id, status);

CREATE INDEX idx_parsing_rules_client_id ON parsing_rules(client_id);
CREATE INDEX idx_parsing_rules_active ON parsing_rules(is_active);
CREATE INDEX idx_parsing_rules_client_active ON parsing_rules(client_id, is_active);
CREATE INDEX idx_parsing_rules_version ON parsing_rules(version);

CREATE INDEX idx_ml_training_data_client_id ON ml_training_data(client_id);
CREATE INDEX idx_ml_training_data_parsing_error_id ON ml_training_data(parsing_error_id);
CREATE INDEX idx_ml_training_data_validation_status ON ml_training_data(validation_status);

-- updated_at 자동 업데이트를 위한 트리거 함수
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- parsing_errors 테이블 updated_at 트리거
DROP TRIGGER IF EXISTS update_parsing_errors_updated_at ON parsing_errors;
CREATE TRIGGER update_parsing_errors_updated_at
    BEFORE UPDATE ON parsing_errors
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- parsing_rules 테이블 updated_at 트리거
DROP TRIGGER IF EXISTS update_parsing_rules_updated_at ON parsing_rules;
CREATE TRIGGER update_parsing_rules_updated_at
    BEFORE UPDATE ON parsing_rules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ml_training_data 테이블 updated_at 트리거
DROP TRIGGER IF EXISTS update_ml_training_data_updated_at ON ml_training_data;
CREATE TRIGGER update_ml_training_data_updated_at
    BEFORE UPDATE ON ml_training_data
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 샘플 데이터 삽입 (테스트용)
INSERT INTO parsing_errors (client_id, transaction_id, receipt_data, error_message, error_type, status) VALUES
    ('client1', 'tx_001_error', '{"store": {"name": ""}, "items": [], "total": null}'::jsonb, '필수 필드 누락: store_name, total_amount', 'VALIDATION_ERROR', 'ERROR'),
    ('client1', 'tx_002_error', '{"invalid": "json", "structure": true}'::jsonb, '파싱 룰 적용 실패: 예상 필드를 찾을 수 없음', 'PARSING_ERROR', 'ERROR'),
    ('client2', 'tx_003_fixed', '{"store_info": {"name": "편의점A"}, "items": [{"name": "음료", "price": 1500}], "total_amount": 1500}'::jsonb, '수정 완료된 파싱 에러', 'PARSING_ERROR', 'FIXED');

INSERT INTO parsing_rules (client_id, rule_name, rule_type, xml_content, description, created_by) VALUES
    ('client1', '기본 영수증 파싱룰', 'GENERAL', '<parsing_rule><field name="store_name" path="$.store.name" required="true"/><field name="total_amount" path="$.payment.total" required="true"/><field name="date" path="$.receipt.date" required="true"/></parsing_rule>', '일반적인 영수증 파싱을 위한 기본 룰', 'admin'),
    ('client2', '편의점 영수증 파싱룰', 'CONVENIENCE_STORE', '<parsing_rule><field name="store_name" path="$.store_info.name" required="true"/><field name="items" path="$.items[*]" required="true"/><field name="total" path="$.total_amount" required="true"/></parsing_rule>', '편의점 영수증 전용 파싱 룰', 'admin');

COMMENT ON TABLE parsing_errors IS '파싱 에러 정보를 저장하는 테이블';
COMMENT ON TABLE parsing_rules IS '파싱 룰 정보를 저장하는 테이블';
COMMENT ON TABLE ml_training_data IS '머신러닝 학습용 데이터를 저장하는 테이블'; 