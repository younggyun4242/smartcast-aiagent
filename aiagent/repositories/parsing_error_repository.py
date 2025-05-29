"""
파싱 에러 Repository
파싱 에러 데이터 액세스 로직 담당 (SOLID: Single Responsibility Principle)
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from aiagent.repositories.base_repository import BaseRepository
from aiagent.models.parsing_error import ParsingError

class ParsingErrorRepository(BaseRepository[ParsingError]):
    """파싱 에러 Repository 클래스"""
    
    def __init__(self, db: Session):
        super().__init__(db, ParsingError)
    
    def get_by_client_id(self, client_id: str, skip: int = 0, limit: int = 100) -> List[ParsingError]:
        """클라이언트 ID로 파싱 에러 조회"""
        return (self.db.query(ParsingError)
                .filter(ParsingError.client_id == client_id)
                .order_by(desc(ParsingError.created_at))
                .offset(skip)
                .limit(limit)
                .all())
    
    def get_by_status(self, status: str, skip: int = 0, limit: int = 100) -> List[ParsingError]:
        """상태별 파싱 에러 조회"""
        return (self.db.query(ParsingError)
                .filter(ParsingError.status == status)
                .order_by(desc(ParsingError.created_at))
                .offset(skip)
                .limit(limit)
                .all())
    
    def get_by_client_and_status(self, client_id: str, status: str, skip: int = 0, limit: int = 100) -> List[ParsingError]:
        """클라이언트 ID와 상태로 파싱 에러 조회"""
        return (self.db.query(ParsingError)
                .filter(and_(ParsingError.client_id == client_id, ParsingError.status == status))
                .order_by(desc(ParsingError.created_at))
                .offset(skip)
                .limit(limit)
                .all())
    
    def search_with_filters(self, client_id: str = None, status: str = None, 
                           skip: int = 0, limit: int = 100) -> Dict[str, Any]:
        """필터를 적용한 검색"""
        query = self.db.query(ParsingError)
        
        # 필터 적용
        if client_id:
            query = query.filter(ParsingError.client_id == client_id)
        if status:
            query = query.filter(ParsingError.status == status)
        
        # 총 개수 조회
        total = query.count()
        
        # 페이징 적용 및 정렬
        errors = (query.order_by(desc(ParsingError.created_at))
                  .offset(skip)
                  .limit(limit)
                  .all())
        
        return {
            "data": errors,
            "total": total,
            "page": (skip // limit) + 1 if limit > 0 else 1,
            "limit": limit
        }
    
    def update_status(self, error_id: int, new_status: str) -> Optional[ParsingError]:
        """파싱 에러 상태 업데이트"""
        error = self.get_by_id(error_id)
        if error:
            error.update_status(new_status)
            self.db.commit()
            self.db.refresh(error)
        return error
    
    def get_error_statistics(self, client_id: str = None) -> Dict[str, int]:
        """에러 통계 조회"""
        query = self.db.query(ParsingError)
        
        if client_id:
            query = query.filter(ParsingError.client_id == client_id)
        
        # 상태별 카운트
        stats = {}
        for status in ["ERROR", "FIXED", "TESTING", "COMPLETED"]:
            stats[status] = query.filter(ParsingError.status == status).count()
        
        stats["TOTAL"] = query.count()
        return stats
    
    def get_recent_errors(self, hours: int = 24, limit: int = 10) -> List[ParsingError]:
        """최근 에러 조회"""
        from datetime import datetime, timedelta
        
        since = datetime.now() - timedelta(hours=hours)
        return (self.db.query(ParsingError)
                .filter(ParsingError.created_at >= since)
                .order_by(desc(ParsingError.created_at))
                .limit(limit)
                .all())
    
    def count_by_client_id(self, client_id: str) -> int:
        """클라이언트별 에러 개수"""
        return self.db.query(ParsingError).filter(ParsingError.client_id == client_id).count()
    
    def bulk_update_status(self, error_ids: List[int], new_status: str) -> int:
        """여러 에러의 상태를 일괄 업데이트"""
        updated_count = (self.db.query(ParsingError)
                        .filter(ParsingError.id.in_(error_ids))
                        .update({ParsingError.status: new_status}, synchronize_session=False))
        self.db.commit()
        return updated_count 