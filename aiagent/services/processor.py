import json
import logging
import time
import traceback
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from .parser import parser, ParserError
from ..api.admin import update_metrics
from ..db.core import SessionLocal
from ..db.models import ReceiptRecord
from ..utils.email_sender import email_sender
from ..core.protocol import MessageFormat
from ..utils.logger import get_logger

# 로깅 설정
logger = get_logger('aiagent.services.processor')

class ProcessingError(Exception):
    """처리 중 발생하는 예외"""
    pass

class BillProcessor:
    """영수증 처리를 위한 비즈니스 로직 처리기"""
    
    def __init__(self):
        logger.debug("[Initialize] BillProcessor 초기화 시작")
        if not parser:
            logger.error("[Initialize] 파서 초기화 실패")
            raise ProcessingError("파서가 초기화되지 않았습니다")
        self.parser = parser
        logger.debug("[Initialize] BillProcessor 초기화 완료")

    def _save_to_db(self, 
                    session: Session,
                    client_id: str,
                    transaction_id: str,
                    raw_data: str,
                    xml_result: Optional[str] = None,
                    is_valid: bool = False,
                    error_message: Optional[str] = None,
                    processing_time: float = 0.0) -> ReceiptRecord:
        """처리 결과를 DB에 저장"""
        try:
            logger.debug(f"[DB Save] 저장 시작 - transaction_id: {transaction_id}")
            logger.debug(f"[DB Save] 상태 - is_valid: {is_valid}, processing_time: {processing_time:.2f}s")
            
            record = ReceiptRecord(
                client_id=client_id,
                transaction_id=transaction_id,
                raw_data=raw_data,
                xml_result=xml_result,
                is_valid=is_valid,
                error_message=error_message,
                processing_time=processing_time
            )
            session.add(record)
            session.commit()
            
            logger.debug("[DB Save] 저장 완료")
            return record
            
        except Exception as e:
            logger.error(f"[DB Save] 저장 실패: {str(e)}")
            logger.error(f"[DB Save] 스택 트레이스:\n{traceback.format_exc()}")
            session.rollback()
            raise ProcessingError(f"DB 저장 실패: {str(e)}")

    def _handle_error(self, 
                     session: Session,
                     client_id: str,
                     transaction_id: str,
                     raw_data: str,
                     error: Exception,
                     processing_time: float) -> Dict[str, Any]:
        """오류 처리 및 기록"""
        logger.error(f"[Error Handler] 오류 발생 - client_id: {client_id}, transaction_id: {transaction_id}")
        logger.error(f"[Error Handler] 오류 내용: {str(error)}")
        logger.error(f"[Error Handler] 스택 트레이스:\n{traceback.format_exc()}")
        
        error_message = str(error)
        
        try:
            # DB에 오류 기록
            logger.debug("[Error Handler] DB에 오류 기록 시도")
            self._save_to_db(
                session=session,
                client_id=client_id,
                transaction_id=transaction_id,
                raw_data=raw_data,
                is_valid=False,
                error_message=error_message,
                processing_time=processing_time
            )
            
            # 이메일 발송
            logger.debug("[Error Handler] 오류 알림 이메일 발송 시도")
            error_data = {
                "client_id": client_id,
                "transaction_id": transaction_id,
                "error_message": error_message,
                "raw_data": raw_data
            }
            email_sender.send_error_notification(error_data)
            
        except Exception as e:
            logger.error(f"[Error Handler] 오류 처리 중 추가 오류 발생: {str(e)}")
            logger.error(f"[Error Handler] 추가 오류 스택 트레이스:\n{traceback.format_exc()}")
        
        # 오류 응답 반환
        return {
            "status": "error",
            "error": error_message,
            "transaction_id": transaction_id
        }

    def process_ai_generate(self, client_id: str, raw_data: bytes) -> Dict[str, Any]:
        """
        AI 생성 요청 처리
        
        Args:
            client_id: 요청 클라이언트 ID
            raw_data: JSON 형식의 바이트 데이터
            
        Returns:
            생성된 파싱 규칙과 버전 정보
        """
        start_time = time.time()
        session = SessionLocal()
        
        logger.debug(f"[AI Generate Start] client_id: {client_id}")
        
        try:
            # JSON 디코딩
            data = json.loads(raw_data.decode('utf-8'))
            transaction_id = data.get("transaction_id", "UNKNOWN")
            
            # 데이터 검증
            if not MessageFormat.validate_ai_generate_data(data):
                raise ProcessingError("AI_GENERATE 필수 필드가 누락되었습니다")
            
            # 파싱 규칙 생성
            result = self.parser.generate_rule(data)
            
            # DB에 결과 저장
            processing_time = time.time() - start_time
            self._save_to_db(
                session=session,
                client_id=client_id,
                transaction_id=transaction_id,
                raw_data=raw_data.decode('utf-8'),
                xml_result=result["rule_xml"],
                is_valid=True,
                processing_time=processing_time
            )
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            return self._handle_error(
                session=session,
                client_id=client_id,
                transaction_id=data.get("transaction_id", "UNKNOWN") if 'data' in locals() else "UNKNOWN",
                raw_data=raw_data.decode(errors='ignore'),
                error=e,
                processing_time=processing_time
            )
        finally:
            session.close()

    def process_ai_merge(self, client_id: str, raw_data: bytes) -> Dict[str, Any]:
        """
        AI 병합 요청 처리
        
        Args:
            client_id: 요청 클라이언트 ID
            raw_data: JSON 형식의 바이트 데이터
            
        Returns:
            병합된 파싱 규칙과 새 버전 정보
        """
        start_time = time.time()
        session = SessionLocal()
        
        logger.debug(f"[AI Merge Start] client_id: {client_id}")
        
        try:
            # JSON 디코딩
            data = json.loads(raw_data.decode('utf-8'))
            transaction_id = data.get("transaction_id", "UNKNOWN")
            
            # 데이터 검증
            if not MessageFormat.validate_ai_merge_data(data):
                raise ProcessingError("AI_MERGE 필수 필드가 누락되었습니다")
            
            # XML 병합
            result = self.parser.merge_rule(
                current_xml=data["current_xml"],
                current_version=data["current_version"],
                receipt_data=data  # 전체 data 객체를 전달 (receipt_data 포함)
            )
            
            # DB에 결과 저장
            processing_time = time.time() - start_time
            self._save_to_db(
                session=session,
                client_id=client_id,
                transaction_id=transaction_id,
                raw_data=raw_data.decode('utf-8'),
                xml_result=result["merged_rule_xml"],
                is_valid=True,
                processing_time=processing_time
            )
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            return self._handle_error(
                session=session,
                client_id=client_id,
                transaction_id=data.get("transaction_id", "UNKNOWN") if 'data' in locals() else "UNKNOWN",
                raw_data=raw_data.decode(errors='ignore'),
                error=e,
                processing_time=processing_time
            )
        finally:
            session.close()

# 싱글톤 인스턴스 생성
try:
    logger.info("[Singleton] BillProcessor 인스턴스 생성 시작")
    bill_processor = BillProcessor()
    logger.info("[Singleton] BillProcessor 인스턴스 생성 완료")
except Exception as e:
    logger.error(f"[Singleton] 영수증 처리기 초기화 실패: {str(e)}")
    logger.error(f"[Singleton] 초기화 실패 스택 트레이스:\n{traceback.format_exc()}")
    bill_processor = None 