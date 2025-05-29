from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float
from datetime import datetime
from .core import Base

class ReceiptRecord(Base):
    """영수증 처리 기록"""
    __tablename__ = "receipt_records"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(String(50), nullable=False, index=True)
    transaction_id = Column(String(100), nullable=False, unique=True, index=True)
    raw_data = Column(Text, nullable=False)  # 원본 JSON 데이터
    parser_xml = Column(Text, nullable=True)  # 파싱 규칙 XML
    xml_result = Column(Text, nullable=True)  # 파싱된 XML 결과
    is_valid = Column(Boolean, default=False)  # XML 구조 검증 결과
    error_message = Column(String(500), nullable=False, default="")  # 오류 메시지
    processing_time = Column(Float, nullable=False)  # 처리 소요 시간 (초)
    created_at = Column(DateTime, default=datetime.utcnow)  # UTC 시간 사용
    
    def to_dict(self):
        """레코드를 딕셔너리로 변환"""
        return {
            "id": self.id,
            "client_id": self.client_id,
            "transaction_id": self.transaction_id,
            "raw_data": self.raw_data,
            "parser_xml": self.parser_xml,
            "xml_result": self.xml_result,
            "is_valid": self.is_valid,
            "error_message": self.error_message,
            "processing_time": self.processing_time,
            "created_at": self.created_at.isoformat() if self.created_at else None
        } 