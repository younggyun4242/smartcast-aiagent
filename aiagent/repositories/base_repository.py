"""
베이스 Repository 클래스
모든 Repository의 공통 인터페이스 정의 (SOLID: Interface Segregation Principle)
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, TypeVar, Generic
from sqlalchemy.orm import Session
from aiagent.database import Base

# 제네릭 타입 정의
T = TypeVar('T', bound=Base)

class BaseRepository(ABC, Generic[T]):
    """추상 베이스 Repository 클래스"""
    
    def __init__(self, db: Session, model_class: type):
        self.db = db
        self.model_class = model_class
    
    def create(self, **kwargs) -> T:
        """새 엔티티 생성"""
        instance = self.model_class(**kwargs)
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance
    
    def get_by_id(self, entity_id: int) -> Optional[T]:
        """ID로 엔티티 조회"""
        return self.db.query(self.model_class).filter(self.model_class.id == entity_id).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """모든 엔티티 조회 (페이징)"""
        return self.db.query(self.model_class).offset(skip).limit(limit).all()
    
    def update(self, entity_id: int, **kwargs) -> Optional[T]:
        """엔티티 업데이트"""
        entity = self.get_by_id(entity_id)
        if entity:
            for key, value in kwargs.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)
            self.db.commit()
            self.db.refresh(entity)
        return entity
    
    def delete(self, entity_id: int) -> bool:
        """엔티티 삭제"""
        entity = self.get_by_id(entity_id)
        if entity:
            self.db.delete(entity)
            self.db.commit()
            return True
        return False
    
    def count(self) -> int:
        """총 엔티티 개수"""
        return self.db.query(self.model_class).count()
    
    def exists(self, entity_id: int) -> bool:
        """엔티티 존재 여부 확인"""
        return self.db.query(self.model_class).filter(self.model_class.id == entity_id).first() is not None
    
    @abstractmethod
    def get_by_client_id(self, client_id: str, skip: int = 0, limit: int = 100) -> List[T]:
        """클라이언트 ID로 엔티티 조회 (각 Repository에서 구현)"""
        pass 