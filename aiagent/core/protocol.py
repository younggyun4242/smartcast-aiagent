"""
ZeroMQ 메시지 프로토콜 정의 v1.0

메시지 형식:
[b'', command, ...args]

프로토콜 버전: 1.0
타임아웃 설정:
- REGISTER: 5초
- HEARTBEAT: 3초
- AI_GENERATE: 30초
- AI_MERGE: 30초

명령어 목록:
1. REGISTER
   - 설명: 클라이언트 등록
   - 요청: [b'', b"REGISTER", client_id, b"", b""]
   - 응답: [b'', b"OK"]
   - 에러: [b'', b"AI_ERROR", client_id, json_error_data]

2. HEARTBEAT
   - 설명: 연결 상태 확인
   - 요청: [b'', b"PING", client_id]
   - 응답: [b'', b"PONG", client_id]
   - 에러: [b'', b"AI_ERROR", client_id, json_error_data]

3. AI_GENERATE
   - 설명: XML 파싱 룰 생성
   - 요청: [b'', b"AI_GENERATE", client_id, json_data]
   - json_data 형식:
     {
         "type": "xml",
         "mode": "GENERATE",
         "client_id": "클라이언트 ID",
         "transaction_id": "고유 거래 ID",
         "receipt_data": {
             "raw_data": "영수증 raw 데이터 (필수)"
         },
         "version": "1.0"
     }
   - 성공 응답: [b'', b"AI_OK", client_id, json_response_data]
     json_response_data = {
         "status": "success",
         "data": {
             "xml_rule": "생성된 XML 규칙",
             "confidence_score": "신뢰도 점수"
         },
         "version": "1.0"
     }
   - 에러 응답: [b'', b"AI_ERROR", client_id, json_error_data]

4. AI_MERGE
   - 설명: 기존 XML과 새로운 데이터 병합
   - 요청: [b'', b"AI_MERGE", client_id, json_data]
   - json_data 형식:
     {
         "type": "xml",
         "mode": "MERGE",
         "client_id": "클라이언트 ID",
         "transaction_id": "고유 거래 ID",
         "receipt_data": {
             "raw_data": "영수증 raw 데이터"
         },
         "current_xml": "현재 XML",
         "current_version": "현재 버전",
         "version": "1.0"
     }
   - 성공 응답: [b'', b"AI_OK", client_id, json_response_data]
     json_response_data = {
         "status": "success",
         "data": {
             "merged_xml": "병합된 XML",
             "changes": "변경사항 목록",
             "confidence_score": "신뢰도 점수"
         },
         "version": "1.0"
     }
   - 에러 응답: [b'', b"AI_ERROR", client_id, json_error_data]

공통 에러 응답 형식:
json_error_data = {
    "status": "error",
    "error_code": "에러 코드",
    "error_message": "에러 메시지",
    "version": "1.0"
}
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

@dataclass
class MessageFormat:
    """메시지 형식 정의"""
    command: bytes
    args: List[bytes]
    version: str = "1.0"
    
    @classmethod
    def create_register(cls, client_id: str) -> List[bytes]:
        """등록 메시지 생성"""
        return [b'', b"REGISTER", client_id.encode(), b"", b""]
    
    @classmethod
    def create_heartbeat(cls, client_id: str) -> List[bytes]:
        """하트비트 메시지 생성"""
        return [b'', b"PING", client_id.encode()]

    @classmethod
    def create_ai_generate(cls, client_id: str, data: Dict[str, Any]) -> List[bytes]:
        """AI 생성 메시지 생성"""
        data["version"] = cls.version
        return [b'', b"AI_GENERATE", client_id.encode(), json.dumps(data).encode()]

    @classmethod
    def create_ai_merge(cls, client_id: str, data: Dict[str, Any]) -> List[bytes]:
        """AI 병합 메시지 생성"""
        data["version"] = cls.version
        return [b'', b"AI_MERGE", client_id.encode(), json.dumps(data).encode()]

    @staticmethod
    def create_success_response(client_id: str, data: Dict[str, Any]) -> List[bytes]:
        """성공 응답 생성"""
        response_data = {
            "status": "success",
            "data": data,
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat()
        }
        return [b'', b"AI_OK", client_id.encode(), json.dumps(response_data).encode()]

    @staticmethod
    def create_error_response(client_id: str, error_code: str, error_message: str) -> List[bytes]:
        """에러 응답 생성"""
        error_data = {
            "status": "error",
            "error_code": error_code,
            "error_message": error_message,
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat()
        }
        return [b'', b"AI_ERROR", client_id.encode(), json.dumps(error_data).encode()]

    @staticmethod
    def validate_receipt_data(receipt_data: Dict[str, Any]) -> bool:
        """영수증 데이터 검증
        
        Args:
            receipt_data: 영수증 데이터 딕셔너리
            
        Returns:
            bool: 검증 결과
            
        검증 항목:
        - receipt_data가 딕셔너리인지
        - raw_data 필드가 존재하는지
        - raw_data가 문자열인지
        """
        return (isinstance(receipt_data, dict) 
                and "raw_data" in receipt_data 
                and isinstance(receipt_data["raw_data"], str))

    @staticmethod
    def validate_ai_generate_data(data: Dict[str, Any]) -> bool:
        """AI 생성 데이터 검증"""
        required_fields = ["type", "mode", "client_id", "transaction_id", "receipt_data", "version"]
        return (all(field in data for field in required_fields)
                and data["mode"] == "GENERATE"
                and MessageFormat.validate_receipt_data(data["receipt_data"]))

    @staticmethod
    def validate_ai_merge_data(data: Dict[str, Any]) -> bool:
        """AI 병합 데이터 검증"""
        required_fields = ["type", "mode", "client_id", "transaction_id", "receipt_data", 
                         "current_xml", "current_version", "version"]
        return (all(field in data for field in required_fields)
                and data["mode"] == "MERGE"
                and MessageFormat.validate_receipt_data(data["receipt_data"]))

    @staticmethod
    def extract_receipt_raw_data(data: Dict[str, Any]) -> str:
        """영수증 raw_data 추출
        
        Args:
            data: 전체 요청 데이터
            
        Returns:
            str: 영수증 raw_data
            
        Raises:
            KeyError: receipt_data나 raw_data가 없는 경우
            ValueError: receipt_data가 올바른 형식이 아닌 경우
        """
        if not isinstance(data.get("receipt_data"), dict):
            raise ValueError("receipt_data must be a dictionary")
        
        raw_data = data["receipt_data"].get("raw_data")
        if not isinstance(raw_data, str):
            raise ValueError("raw_data must be a string")
            
        return raw_data

# 메시지 타입 상수
class MessageType:
    """메시지 타입 정의"""
    REGISTER = b"REGISTER"
    OK = b"OK"
    PING = b"PING"
    PONG = b"PONG"
    AI_GENERATE = b"AI_GENERATE"
    AI_MERGE = b"AI_MERGE"
    AI_OK = b"AI_OK"
    AI_ERROR = b"AI_ERROR"

# 타임아웃 설정 (초)
class Timeout:
    """각 명령어별 타임아웃 설정"""
    REGISTER = 5
    HEARTBEAT = 3
    AI_GENERATE = 30
    AI_MERGE = 30

# 에러 코드
class ErrorCode:
    """
    에러 코드 정의:
    - INVALID_FORMAT: 메시지 형식이 잘못된 경우
    - INVALID_COMMAND: 존재하지 않는 명령어
    - INVALID_DATA: 요청 데이터 형식이 잘못된 경우
    - INVALID_RECEIPT: 영수증 데이터 형식이 잘못된 경우
    - TIMEOUT: 요청 처리 시간 초과
    - AI_ERROR: AI 처리 중 발생한 오류
    - VERSION_MISMATCH: 프로토콜 버전 불일치
    """
    INVALID_FORMAT = "INVALID_FORMAT"
    INVALID_COMMAND = "INVALID_COMMAND"
    INVALID_DATA = "INVALID_DATA"
    INVALID_RECEIPT = "INVALID_RECEIPT"
    TIMEOUT = "TIMEOUT"
    AI_ERROR = "AI_ERROR"
    VERSION_MISMATCH = "VERSION_MISMATCH" 