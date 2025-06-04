"""
파싱 룰 Repository
파싱 룰 데이터 액세스 로직 담당 (SOLID: Single Responsibility Principle)
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from aiagent.repositories.base_repository import BaseRepository
from aiagent.models.parsing_rule import ParsingRule

class ParsingRuleRepository(BaseRepository[ParsingRule]):
    """파싱 룰 Repository 클래스"""
    
    def __init__(self, db: Session):
        super().__init__(db, ParsingRule)
    
    def get_by_client_id(self, client_id: str, skip: int = 0, limit: int = 100) -> List[ParsingRule]:
        """클라이언트 ID로 파싱 룰 조회"""
        return (self.db.query(ParsingRule)
                .filter(ParsingRule.client_id == client_id)
                .order_by(desc(ParsingRule.created_at))
                .offset(skip)
                .limit(limit)
                .all())
    
    def get_active_rules_by_client(self, client_id: str) -> List[ParsingRule]:
        """클라이언트의 활성 파싱 룰 조회"""
        return (self.db.query(ParsingRule)
                .filter(and_(ParsingRule.client_id == client_id, ParsingRule.is_active == True))
                .order_by(desc(ParsingRule.version))
                .all())
    
    def get_by_client_and_type(self, client_id: str, rule_type: str) -> List[ParsingRule]:
        """클라이언트 ID와 룰 타입으로 조회"""
        return (self.db.query(ParsingRule)
                .filter(and_(ParsingRule.client_id == client_id, ParsingRule.rule_type == rule_type))
                .order_by(desc(ParsingRule.version))
                .all())
    
    def get_latest_version_by_client_and_type(self, client_id: str, rule_type: str) -> Optional[ParsingRule]:
        """클라이언트와 타입별 최신 버전 룰 조회"""
        return (self.db.query(ParsingRule)
                .filter(and_(
                    ParsingRule.client_id == client_id,
                    ParsingRule.rule_type == rule_type,
                    ParsingRule.is_active == True
                ))
                .order_by(desc(ParsingRule.version))
                .first())
    
    def create_new_version(self, client_id: str, rule_type: str, xml_content: str) -> ParsingRule:
        """새 버전의 파싱 룰 생성"""
        # 기존 최신 버전 확인
        latest_rule = self.get_latest_version_by_client_and_type(client_id, rule_type)
        new_version = (latest_rule.version + 1) if latest_rule else 1
        
        # 새 룰 생성
        new_rule = ParsingRule.create(
            client_id=client_id,
            rule_type=rule_type,
            xml_content=xml_content,
            version=new_version,
            is_active=True
        )
        
        self.db.add(new_rule)
        self.db.commit()
        self.db.refresh(new_rule)
        
        return new_rule
    
    def deactivate_old_versions(self, client_id: str, rule_type: str, except_version: int = None) -> int:
        """이전 버전들을 비활성화"""
        query = self.db.query(ParsingRule).filter(and_(
            ParsingRule.client_id == client_id,
            ParsingRule.rule_type == rule_type
        ))
        
        if except_version:
            query = query.filter(ParsingRule.version != except_version)
        
        updated_count = query.update({ParsingRule.is_active: False}, synchronize_session=False)
        self.db.commit()
        return updated_count
    
    def update_xml_content(self, rule_id: int, xml_content: str) -> Optional[ParsingRule]:
        """XML 내용 업데이트"""
        rule = self.get_by_id(rule_id)
        if rule:
            rule.update_xml_content(xml_content)
            self.db.commit()
            self.db.refresh(rule)
        return rule
    
    def search_rules(self, client_id: str = None, rule_type: str = None, 
                    is_active: bool = None, skip: int = 0, limit: int = 100) -> Dict[str, Any]:
        """파싱 룰 검색"""
        query = self.db.query(ParsingRule)
        
        # 필터 적용
        if client_id:
            query = query.filter(ParsingRule.client_id == client_id)
        if rule_type:
            query = query.filter(ParsingRule.rule_type == rule_type)
        if is_active is not None:
            query = query.filter(ParsingRule.is_active == is_active)
        
        # 총 개수 조회
        total = query.count()
        
        # 페이징 적용 및 정렬
        rules = (query.order_by(desc(ParsingRule.created_at))
                 .offset(skip)
                 .limit(limit)
                 .all())
        
        return {
            "data": rules,
            "total": total,
            "page": (skip // limit) + 1 if limit > 0 else 1,
            "limit": limit
        }
    
    def get_rule_statistics(self, client_id: str = None) -> Dict[str, Any]:
        """룰 통계 조회"""
        query = self.db.query(ParsingRule)
        
        if client_id:
            query = query.filter(ParsingRule.client_id == client_id)
        
        total_rules = query.count()
        active_rules = query.filter(ParsingRule.is_active == True).count()
        inactive_rules = total_rules - active_rules
        
        # 타입별 카운트
        type_counts = {}
        for rule in query.all():
            rule_type = rule.rule_type
            if rule_type not in type_counts:
                type_counts[rule_type] = {"total": 0, "active": 0}
            type_counts[rule_type]["total"] += 1
            if rule.is_active:
                type_counts[rule_type]["active"] += 1
        
        return {
            "total_rules": total_rules,
            "active_rules": active_rules,
            "inactive_rules": inactive_rules,
            "type_counts": type_counts
        }
    
    def clone_rule(self, rule_id: int, new_client_id: str = None) -> Optional[ParsingRule]:
        """룰 복제"""
        original_rule = self.get_by_id(rule_id)
        if not original_rule:
            return None
        
        new_rule = ParsingRule.create(
            client_id=new_client_id or original_rule.client_id,
            rule_type=original_rule.rule_type,
            xml_content=original_rule.xml_content,
            version=1,  # 새 클라이언트의 경우 버전 1부터 시작
            is_active=False  # 기본적으로 비활성 상태로 생성
        )
        
        self.db.add(new_rule)
        self.db.commit()
        self.db.refresh(new_rule)
        
        return new_rule 