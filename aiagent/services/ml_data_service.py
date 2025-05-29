"""
ML 데이터 서비스
머신러닝 훈련 데이터 관리, 데이터 검증, 내보내기 등의 비즈니스 로직을 담당
SOLID: Single Responsibility, Dependency Inversion 적용
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from aiagent.repositories.ml_training_data_repository import MLTrainingDataRepository
from aiagent.models.ml_training_data import MLTrainingData
from aiagent.exceptions import NotFoundError, ValidationError, BusinessLogicError
from aiagent.utils.logger import get_logger

logger = get_logger(__name__)

class MLDataService:
    """ML 데이터 서비스 클래스"""
    
    def __init__(self, db: Session):
        # 의존성 주입: Repository를 주입받아 사용
        self.db = db
        self.ml_data_repo = MLTrainingDataRepository(db)
    
    # === 훈련 데이터 조회 기능 ===
    
    def get_training_data(self, client_id: str = None, page: int = 1, 
                         limit: int = 50) -> Dict[str, Any]:
        """ML 훈련 데이터 조회 (페이징 포함)"""
        try:
            skip = (page - 1) * limit
            
            if client_id:
                training_data = self.ml_data_repo.get_by_client_id(
                    client_id=client_id, skip=skip, limit=limit
                )
                total = self.ml_data_repo.count_by_client_id(client_id)
            else:
                training_data = self.ml_data_repo.get_all(skip=skip, limit=limit)
                total = self.ml_data_repo.count()
            
            # 모델을 딕셔너리로 변환
            data = [item.to_dict() for item in training_data]
            
            result = {
                "data": data,
                "total": total,
                "page": page,
                "limit": limit
            }
            
            logger.info(f"훈련 데이터 조회 완료: {total}건 중 {len(data)}건 반환")
            return result
            
        except Exception as e:
            logger.error(f"훈련 데이터 조회 중 오류 발생: {e}")
            raise BusinessLogicError(f"훈련 데이터 조회 실패: {str(e)}")
    
    def get_training_data_by_period(self, days: int = 30, client_id: str = None) -> List[Dict[str, Any]]:
        """기간별 훈련 데이터 조회"""
        try:
            training_data = self.ml_data_repo.get_training_data_for_period(
                days=days, client_id=client_id
            )
            
            result = [item.to_dict() for item in training_data]
            
            logger.info(f"기간별 훈련 데이터 조회 완료: 최근 {days}일, {len(result)}건")
            return result
            
        except Exception as e:
            logger.error(f"기간별 훈련 데이터 조회 중 오류 발생: {e}")
            raise BusinessLogicError(f"기간별 훈련 데이터 조회 실패: {str(e)}")
    
    def get_training_data_statistics(self, client_id: str = None, 
                                   days: int = None) -> Dict[str, Any]:
        """훈련 데이터 통계 조회"""
        try:
            stats = self.ml_data_repo.get_statistics(client_id=client_id, days=days)
            
            # 추가 통계 정보 계산
            enhanced_stats = {
                **stats,
                "period_days": days if days else "전체",
                "avg_daily_count": self._calculate_avg_daily_count(stats, days)
            }
            
            logger.info(f"훈련 데이터 통계 조회 완료: {enhanced_stats}")
            return enhanced_stats
            
        except Exception as e:
            logger.error(f"훈련 데이터 통계 조회 중 오류 발생: {e}")
            raise BusinessLogicError(f"훈련 데이터 통계 조회 실패: {str(e)}")
    
    # === 훈련 데이터 저장 기능 ===
    
    def create_training_data(self, client_id: str, receipt_data: dict, 
                           xml_result: str, parsing_error_id: int = None) -> Dict[str, Any]:
        """새 훈련 데이터 생성"""
        try:
            # 데이터 검증
            self._validate_training_data(client_id, receipt_data, xml_result)
            
            # 훈련 데이터 생성
            training_data = self.ml_data_repo.create_from_error(
                client_id=client_id,
                receipt_data=receipt_data,
                xml_result=xml_result,
                parsing_error_id=parsing_error_id
            )
            
            logger.info(f"훈련 데이터 생성 완료: ID {training_data.id}")
            return training_data.to_dict()
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"훈련 데이터 생성 중 오류 발생: {e}")
            raise BusinessLogicError(f"훈련 데이터 생성 실패: {str(e)}")
    
    def bulk_create_training_data(self, training_data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """여러 훈련 데이터 일괄 생성"""
        try:
            created_count = 0
            failed_count = 0
            errors = []
            
            for data in training_data_list:
                try:
                    self.create_training_data(
                        client_id=data.get('client_id'),
                        receipt_data=data.get('receipt_data'),
                        xml_result=data.get('xml_result'),
                        parsing_error_id=data.get('parsing_error_id')
                    )
                    created_count += 1
                except Exception as e:
                    failed_count += 1
                    errors.append(str(e))
            
            result = {
                "success": True,
                "created_count": created_count,
                "failed_count": failed_count,
                "total_count": len(training_data_list),
                "errors": errors[:10]  # 최대 10개의 오류만 반환
            }
            
            logger.info(f"훈련 데이터 일괄 생성 완료: 성공 {created_count}건, 실패 {failed_count}건")
            return result
            
        except Exception as e:
            logger.error(f"훈련 데이터 일괄 생성 중 오류 발생: {e}")
            raise BusinessLogicError(f"훈련 데이터 일괄 생성 실패: {str(e)}")
    
    # === 데이터 검증 기능 ===
    
    def validate_training_data_quality(self, client_id: str = None) -> Dict[str, Any]:
        """훈련 데이터 품질 검증"""
        try:
            # 유효한 데이터 조회
            valid_data = self.ml_data_repo.get_valid_training_data(client_id=client_id)
            
            # 전체 데이터와 비교
            if client_id:
                total_data = self.ml_data_repo.get_by_client_id(client_id)
            else:
                total_data = self.ml_data_repo.get_all()
            
            total_count = len(total_data)
            valid_count = len(valid_data)
            invalid_count = total_count - valid_count
            
            quality_score = (valid_count / total_count * 100) if total_count > 0 else 0
            
            result = {
                "total_count": total_count,
                "valid_count": valid_count,
                "invalid_count": invalid_count,
                "quality_score": round(quality_score, 2),
                "quality_level": self._get_quality_level(quality_score)
            }
            
            logger.info(f"훈련 데이터 품질 검증 완료: {result}")
            return result
            
        except Exception as e:
            logger.error(f"훈련 데이터 품질 검증 중 오류 발생: {e}")
            raise BusinessLogicError(f"훈련 데이터 품질 검증 실패: {str(e)}")
    
    def cleanup_invalid_data(self, client_id: str = None) -> Dict[str, Any]:
        """무효한 훈련 데이터 정리"""
        try:
            # 모든 데이터 조회
            if client_id:
                all_data = self.ml_data_repo.get_by_client_id(client_id)
            else:
                all_data = self.ml_data_repo.get_all()
            
            deleted_count = 0
            for data in all_data:
                if not data.validate_data():
                    self.ml_data_repo.delete(data.id)
                    deleted_count += 1
            
            result = {
                "success": True,
                "deleted_count": deleted_count,
                "remaining_count": len(all_data) - deleted_count
            }
            
            logger.info(f"무효한 훈련 데이터 정리 완료: {deleted_count}건 삭제")
            return result
            
        except Exception as e:
            logger.error(f"무효한 훈련 데이터 정리 중 오류 발생: {e}")
            raise BusinessLogicError(f"무효한 훈련 데이터 정리 실패: {str(e)}")
    
    # === 데이터 내보내기 기능 ===
    
    def export_training_data(self, client_id: str = None, limit: int = 1000, 
                           format: str = "json") -> Dict[str, Any]:
        """훈련 데이터 내보내기"""
        try:
            data = self.ml_data_repo.export_training_data(client_id=client_id, limit=limit)
            
            if format.lower() == "csv":
                # CSV 형태로 변환
                csv_data = self._convert_to_csv(data)
                result = {
                    "format": "csv",
                    "data": csv_data,
                    "count": len(data)
                }
            else:
                # JSON 형태로 반환
                result = {
                    "format": "json",
                    "data": data,
                    "count": len(data)
                }
            
            logger.info(f"훈련 데이터 내보내기 완료: {len(data)}건, 형식: {format}")
            return result
            
        except Exception as e:
            logger.error(f"훈련 데이터 내보내기 중 오류 발생: {e}")
            raise BusinessLogicError(f"훈련 데이터 내보내기 실패: {str(e)}")
    
    def delete_old_training_data(self, days: int = 365) -> Dict[str, Any]:
        """오래된 훈련 데이터 삭제"""
        try:
            deleted_count = self.ml_data_repo.delete_old_training_data(days=days)
            
            result = {
                "success": True,
                "deleted_count": deleted_count,
                "retention_days": days
            }
            
            logger.info(f"오래된 훈련 데이터 삭제 완료: {deleted_count}건 삭제 ({days}일 이전)")
            return result
            
        except Exception as e:
            logger.error(f"오래된 훈련 데이터 삭제 중 오류 발생: {e}")
            raise BusinessLogicError(f"오래된 훈련 데이터 삭제 실패: {str(e)}")
    
    # === 검색 기능 ===
    
    def search_training_data(self, search_term: str, client_id: str = None, 
                           page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """훈련 데이터 검색"""
        try:
            skip = (page - 1) * limit
            data = self.ml_data_repo.search_by_content(
                search_term=search_term,
                client_id=client_id,
                skip=skip,
                limit=limit
            )
            
            result = {
                "data": [item.to_dict() for item in data],
                "search_term": search_term,
                "count": len(data),
                "page": page,
                "limit": limit
            }
            
            logger.info(f"훈련 데이터 검색 완료: '{search_term}', {len(data)}건 발견")
            return result
            
        except Exception as e:
            logger.error(f"훈련 데이터 검색 중 오류 발생: {e}")
            raise BusinessLogicError(f"훈련 데이터 검색 실패: {str(e)}")
    
    # === 유틸리티 메서드 ===
    
    def _validate_training_data(self, client_id: str, receipt_data: dict, xml_result: str):
        """훈련 데이터 유효성 검증"""
        if not client_id or not client_id.strip():
            raise ValidationError("클라이언트 ID가 필요합니다")
        
        if not isinstance(receipt_data, dict):
            raise ValidationError("영수증 데이터는 딕셔너리 형태여야 합니다")
        
        if not xml_result or not xml_result.strip():
            raise ValidationError("XML 결과가 필요합니다")
        
        # XML 형식 검증
        if not (xml_result.strip().startswith('<') and xml_result.strip().endswith('>')):
            raise ValidationError("XML 결과가 올바른 형식이 아닙니다")
    
    def _calculate_avg_daily_count(self, stats: dict, days: int = None) -> float:
        """일평균 생성 개수 계산"""
        try:
            if not days or "daily_counts" not in stats:
                return 0.0
            
            daily_counts = stats["daily_counts"]
            if not daily_counts:
                return 0.0
            
            total_count = sum(daily_counts.values())
            return round(total_count / len(daily_counts), 2)
            
        except Exception:
            return 0.0
    
    def _get_quality_level(self, quality_score: float) -> str:
        """품질 점수에 따른 등급 반환"""
        if quality_score >= 95:
            return "최고"
        elif quality_score >= 85:
            return "우수"
        elif quality_score >= 70:
            return "보통"
        elif quality_score >= 50:
            return "낮음"
        else:
            return "매우 낮음"
    
    def _convert_to_csv(self, data: List[dict]) -> str:
        """JSON 데이터를 CSV 형태로 변환"""
        try:
            if not data:
                return ""
            
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
            
            return output.getvalue()
            
        except Exception:
            return "" 