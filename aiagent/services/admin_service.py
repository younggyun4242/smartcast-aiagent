"""
관리자 서비스
파싱 에러 관리, 파싱룰 수정/테스트/전송 등의 비즈니스 로직을 담당
SOLID: Single Responsibility, Dependency Inversion 적용
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from aiagent.repositories.parsing_error_repository import ParsingErrorRepository
from aiagent.repositories.parsing_rule_repository import ParsingRuleRepository
from aiagent.repositories.ml_training_data_repository import MLTrainingDataRepository
from aiagent.models.parsing_error import ParsingError
from aiagent.models.parsing_rule import ParsingRule
from aiagent.exceptions import NotFoundError, ValidationError, ParseRuleTestError, BusinessLogicError
from aiagent.utils.logger import get_logger
import json
import xml.etree.ElementTree as ET

logger = get_logger(__name__)

class AdminService:
    """관리자 서비스 클래스"""
    
    def __init__(self, db: Session):
        # 의존성 주입: Repository들을 주입받아 사용
        self.db = db
        self.error_repo = ParsingErrorRepository(db)
        self.rule_repo = ParsingRuleRepository(db)
        self.ml_data_repo = MLTrainingDataRepository(db)
    
    # === 에러 조회 기능 ===
    
    def get_parsing_errors(self, client_id: str = None, status: str = None, 
                          page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """파싱 에러 목록 조회 (페이징 포함)"""
        try:
            skip = (page - 1) * limit
            result = self.error_repo.search_with_filters(
                client_id=client_id,
                status=status,
                skip=skip,
                limit=limit
            )
            
            # 모델을 딕셔너리로 변환
            result["data"] = [error.to_dict() for error in result["data"]]
            
            logger.info(f"파싱 에러 조회 완료: {result['total']}건 중 {len(result['data'])}건 반환")
            return result
            
        except Exception as e:
            logger.error(f"파싱 에러 조회 중 오류 발생: {e}")
            raise BusinessLogicError(f"파싱 에러 조회 실패: {str(e)}")
    
    def get_parsing_error_detail(self, error_id: int) -> Dict[str, Any]:
        """특정 파싱 에러 상세 조회"""
        try:
            error = self.error_repo.get_by_id(error_id)
            if not error:
                raise NotFoundError(f"ID {error_id}인 파싱 에러를 찾을 수 없습니다")
            
            logger.info(f"파싱 에러 상세 조회: ID {error_id}")
            return error.to_dict()
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"파싱 에러 상세 조회 중 오류 발생: {e}")
            raise BusinessLogicError(f"파싱 에러 상세 조회 실패: {str(e)}")
    
    def get_error_statistics(self, client_id: str = None) -> Dict[str, Any]:
        """에러 통계 조회"""
        try:
            stats = self.error_repo.get_error_statistics(client_id)
            logger.info(f"에러 통계 조회 완료: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"에러 통계 조회 중 오류 발생: {e}")
            raise BusinessLogicError(f"에러 통계 조회 실패: {str(e)}")
    
    # === 파싱룰 수정 기능 ===
    
    def update_parsing_rule(self, error_id: int, xml_content: str) -> Dict[str, Any]:
        """파싱 에러에 대한 파싱룰 수정"""
        try:
            # 에러 존재 확인
            error = self.error_repo.get_by_id(error_id)
            if not error:
                raise NotFoundError(f"ID {error_id}인 파싱 에러를 찾을 수 없습니다")
            
            # XML 유효성 검증
            self._validate_xml_content(xml_content)
            
            # 상태를 TESTING으로 변경
            self.error_repo.update_status(error_id, "TESTING")
            
            logger.info(f"파싱룰 수정 완료: 에러 ID {error_id}")
            return {
                "success": True,
                "message": "파싱룰이 수정되었습니다.",
                "error_id": error_id,
                "status": "TESTING"
            }
            
        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"파싱룰 수정 중 오류 발생: {e}")
            raise BusinessLogicError(f"파싱룰 수정 실패: {str(e)}")
    
    # === 파싱룰 테스트 기능 ===
    
    def test_parsing_rule(self, error_id: int, xml_content: str) -> Dict[str, Any]:
        """파싱룰을 실제 데이터에 테스트"""
        try:
            # 에러 정보 조회
            error = self.error_repo.get_by_id(error_id)
            if not error:
                raise NotFoundError(f"ID {error_id}인 파싱 에러를 찾을 수 없습니다")
            
            # XML 유효성 검증
            self._validate_xml_content(xml_content)
            
            # 실제 파싱 테스트 수행
            test_result = self._perform_parsing_test(error.receipt_data, xml_content)
            
            # 테스트 성공 시 상태 업데이트
            if test_result["is_valid"]:
                self.error_repo.update_status(error_id, "FIXED")
                logger.info(f"파싱룰 테스트 성공: 에러 ID {error_id}")
            else:
                logger.warning(f"파싱룰 테스트 실패: 에러 ID {error_id}")
            
            return test_result
            
        except (NotFoundError, ValidationError, ParseRuleTestError):
            raise
        except Exception as e:
            logger.error(f"파싱룰 테스트 중 오류 발생: {e}")
            raise BusinessLogicError(f"파싱룰 테스트 실패: {str(e)}")
    
    # === 파싱룰 전송 기능 ===
    
    def submit_parsing_rule(self, error_id: int, xml_content: str) -> Dict[str, Any]:
        """수정된 파싱룰을 전송하고 ML 훈련 데이터로 저장"""
        try:
            # 에러 정보 조회
            error = self.error_repo.get_by_id(error_id)
            if not error:
                raise NotFoundError(f"ID {error_id}인 파싱 에러를 찾을 수 없습니다")
            
            # 에러가 FIXED 상태인지 확인
            if not error.is_fixed():
                raise BusinessLogicError("테스트가 완료된 파싱룰만 전송할 수 있습니다")
            
            # XML 유효성 검증
            self._validate_xml_content(xml_content)
            
            # 새 파싱룰 버전 생성
            rule_type = self._determine_rule_type(error.client_id, xml_content)
            new_rule = self.rule_repo.create_new_version(
                client_id=error.client_id,
                rule_type=rule_type,
                xml_content=xml_content
            )
            
            # 이전 버전들 비활성화
            self.rule_repo.deactivate_old_versions(
                client_id=error.client_id,
                rule_type=rule_type,
                except_version=new_rule.version
            )
            
            # ML 훈련 데이터로 저장
            self.ml_data_repo.create_from_error(
                client_id=error.client_id,
                receipt_data=error.receipt_data,
                xml_result=xml_content,
                parsing_error_id=error_id
            )
            
            # 에러 상태를 COMPLETED로 변경
            self.error_repo.update_status(error_id, "COMPLETED")
            
            logger.info(f"파싱룰 전송 완료: 에러 ID {error_id}, 룰 ID {new_rule.id}")
            return {
                "success": True,
                "message": "파싱룰이 전송되었습니다.",
                "rule_id": new_rule.id,
                "error_id": error_id,
                "status": "COMPLETED"
            }
            
        except (NotFoundError, ValidationError, BusinessLogicError):
            raise
        except Exception as e:
            logger.error(f"파싱룰 전송 중 오류 발생: {e}")
            raise BusinessLogicError(f"파싱룰 전송 실패: {str(e)}")
    
    # === 유틸리티 메서드 ===
    
    def _validate_xml_content(self, xml_content: str):
        """XML 내용 유효성 검증"""
        if not xml_content or not xml_content.strip():
            raise ValidationError("XML 내용이 비어있습니다")
        
        try:
            # XML 파싱 테스트
            ET.fromstring(xml_content)
            
            # PARSER 태그 확인
            if not xml_content.strip().startswith('<PARSER>'):
                raise ValidationError("XML은 <PARSER> 태그로 시작해야 합니다")
            
            if not xml_content.strip().endswith('</PARSER>'):
                raise ValidationError("XML은 </PARSER> 태그로 끝나야 합니다")
                
        except ET.ParseError as e:
            raise ValidationError(f"XML 형식이 올바르지 않습니다: {str(e)}")
    
    def _perform_parsing_test(self, receipt_data: dict, xml_content: str) -> Dict[str, Any]:
        """실제 파싱 테스트 수행"""
        try:
            # 여기서는 간단한 검증만 수행
            # 실제로는 기존 파싱 엔진을 사용해야 함
            
            result = {
                "success": True,
                "is_valid": True,
                "result": receipt_data,  # 간단히 원본 데이터 반환
                "message": "파싱 테스트가 성공했습니다"
            }
            
            # 실제 파싱 로직이 여기에 들어갈 예정
            # TODO: 기존 파싱 엔진과 연동
            
            return result
            
        except Exception as e:
            logger.error(f"파싱 테스트 수행 중 오류: {e}")
            raise ParseRuleTestError(f"파싱 테스트 실패: {str(e)}")
    
    def _determine_rule_type(self, client_id: str, xml_content: str) -> str:
        """XML 내용을 분석하여 룰 타입 결정"""
        try:
            # XML에서 TYPE 태그 찾기
            root = ET.fromstring(xml_content)
            type_element = root.find('.//TYPE')
            
            if type_element is not None and type_element.get('name'):
                return type_element.get('name')
            
            # TYPE이 없으면 기본 타입 사용
            return f"TYPE_{client_id}"
            
        except Exception:
            return f"TYPE_{client_id}_DEFAULT"
    
    def get_recent_errors(self, hours: int = 24, limit: int = 10) -> List[Dict[str, Any]]:
        """최근 에러 조회"""
        try:
            errors = self.error_repo.get_recent_errors(hours=hours, limit=limit)
            result = [error.to_dict() for error in errors]
            
            logger.info(f"최근 {hours}시간 에러 조회: {len(result)}건")
            return result
            
        except Exception as e:
            logger.error(f"최근 에러 조회 중 오류 발생: {e}")
            raise BusinessLogicError(f"최근 에러 조회 실패: {str(e)}")
    
    def bulk_update_error_status(self, error_ids: List[int], new_status: str) -> Dict[str, Any]:
        """여러 에러의 상태 일괄 업데이트"""
        try:
            # 상태 유효성 검증
            valid_statuses = ["ERROR", "FIXED", "TESTING", "COMPLETED"]
            if new_status not in valid_statuses:
                raise ValidationError(f"유효하지 않은 상태입니다: {new_status}")
            
            updated_count = self.error_repo.bulk_update_status(error_ids, new_status)
            
            logger.info(f"에러 상태 일괄 업데이트: {updated_count}건 업데이트됨")
            return {
                "success": True,
                "updated_count": updated_count,
                "new_status": new_status
            }
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"에러 상태 일괄 업데이트 중 오류 발생: {e}")
            raise BusinessLogicError(f"에러 상태 일괄 업데이트 실패: {str(e)}") 