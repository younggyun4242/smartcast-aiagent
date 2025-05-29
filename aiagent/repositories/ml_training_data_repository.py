"""
ML 훈련 데이터 Repository
머신러닝 학습용 데이터 액세스 로직 담당 (SOLID: Single Responsibility Principle)
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func
from aiagent.repositories.base_repository import BaseRepository
from aiagent.models.ml_training_data import MLTrainingData

class MLTrainingDataRepository(BaseRepository[MLTrainingData]):
    """ML 훈련 데이터 Repository 클래스"""
    
    def __init__(self, db: Session):
        super().__init__(db, MLTrainingData)
    
    def get_by_client_id(self, client_id: str, skip: int = 0, limit: int = 100) -> List[MLTrainingData]:
        """클라이언트 ID로 ML 훈련 데이터 조회"""
        return (self.db.query(MLTrainingData)
                .filter(MLTrainingData.client_id == client_id)
                .order_by(desc(MLTrainingData.created_at))
                .offset(skip)
                .limit(limit)
                .all())
    
    def get_by_parsing_error_id(self, parsing_error_id: int) -> List[MLTrainingData]:
        """파싱 에러 ID로 연관된 훈련 데이터 조회"""
        return (self.db.query(MLTrainingData)
                .filter(MLTrainingData.parsing_error_id == parsing_error_id)
                .order_by(desc(MLTrainingData.created_at))
                .all())
    
    def create_from_error(self, client_id: str, receipt_data: dict, xml_result: str, 
                         parsing_error_id: int) -> MLTrainingData:
        """파싱 에러에서 ML 훈련 데이터 생성"""
        training_data = MLTrainingData.create(
            client_id=client_id,
            receipt_data=receipt_data,
            xml_result=xml_result,
            parsing_error_id=parsing_error_id
        )
        
        self.db.add(training_data)
        self.db.commit()
        self.db.refresh(training_data)
        
        return training_data
    
    def get_training_data_for_period(self, days: int = 30, client_id: str = None) -> List[MLTrainingData]:
        """특정 기간의 훈련 데이터 조회"""
        since = datetime.now() - timedelta(days=days)
        query = self.db.query(MLTrainingData).filter(MLTrainingData.created_at >= since)
        
        if client_id:
            query = query.filter(MLTrainingData.client_id == client_id)
        
        return query.order_by(desc(MLTrainingData.created_at)).all()
    
    def get_statistics(self, client_id: str = None, days: int = None) -> Dict[str, Any]:
        """훈련 데이터 통계 조회"""
        query = self.db.query(MLTrainingData)
        
        if client_id:
            query = query.filter(MLTrainingData.client_id == client_id)
        
        if days:
            since = datetime.now() - timedelta(days=days)
            query = query.filter(MLTrainingData.created_at >= since)
        
        # 기본 통계
        total_count = query.count()
        
        # 클라이언트별 카운트
        client_counts = {}
        if not client_id:  # 전체 조회인 경우
            client_results = (self.db.query(MLTrainingData.client_id, func.count(MLTrainingData.id))
                             .group_by(MLTrainingData.client_id)
                             .all())
            client_counts = {client: count for client, count in client_results}
        
        # 날짜별 카운트 (최근 7일)
        daily_counts = {}
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).date()
            daily_count = (query.filter(func.date(MLTrainingData.created_at) == date).count())
            daily_counts[date.isoformat()] = daily_count
        
        return {
            "total_count": total_count,
            "client_counts": client_counts,
            "daily_counts": daily_counts
        }
    
    def export_training_data(self, client_id: str = None, limit: int = 1000) -> List[Dict[str, Any]]:
        """훈련 데이터 내보내기 (ML 학습용)"""
        query = self.db.query(MLTrainingData)
        
        if client_id:
            query = query.filter(MLTrainingData.client_id == client_id)
        
        training_data = query.limit(limit).all()
        
        return [
            {
                "id": data.id,
                "client_id": data.client_id,
                "receipt_data": data.receipt_data,
                "xml_result": data.xml_result,
                "created_at": data.created_at.isoformat()
            }
            for data in training_data
        ]
    
    def get_valid_training_data(self, client_id: str = None, skip: int = 0, limit: int = 100) -> List[MLTrainingData]:
        """유효성 검증을 통과한 훈련 데이터만 조회"""
        query = self.db.query(MLTrainingData)
        
        if client_id:
            query = query.filter(MLTrainingData.client_id == client_id)
        
        training_data = query.offset(skip).limit(limit).all()
        
        # 유효한 데이터만 필터링
        valid_data = []
        for data in training_data:
            if data.validate_data():
                valid_data.append(data)
        
        return valid_data
    
    def delete_old_training_data(self, days: int = 365) -> int:
        """오래된 훈련 데이터 삭제"""
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = (self.db.query(MLTrainingData)
                        .filter(MLTrainingData.created_at < cutoff_date)
                        .delete())
        self.db.commit()
        return deleted_count
    
    def search_by_content(self, search_term: str, client_id: str = None, 
                         skip: int = 0, limit: int = 100) -> List[MLTrainingData]:
        """XML 결과 내용으로 검색"""
        query = self.db.query(MLTrainingData)
        
        if client_id:
            query = query.filter(MLTrainingData.client_id == client_id)
        
        # PostgreSQL의 경우 텍스트 검색 사용
        query = query.filter(MLTrainingData.xml_result.contains(search_term))
        
        return (query.order_by(desc(MLTrainingData.created_at))
                .offset(skip)
                .limit(limit)
                .all())
    
    def get_data_by_amount_range(self, min_amount: float = None, max_amount: float = None,
                                client_id: str = None) -> List[MLTrainingData]:
        """금액 범위로 훈련 데이터 조회"""
        training_data = self.get_by_client_id(client_id) if client_id else self.get_all()
        
        filtered_data = []
        for data in training_data:
            total_amount = data.get_total_amount()
            
            if min_amount is not None and total_amount < min_amount:
                continue
            if max_amount is not None and total_amount > max_amount:
                continue
                
            filtered_data.append(data)
        
        return filtered_data 