"""
API 의존성 주입
FastAPI Dependency Injection을 위한 함수들 정의
"""

from typing import Generator
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from aiagent.database import get_db, check_db_connection
from aiagent.services.admin_service import AdminService
from aiagent.services.ml_data_service import MLDataService
from aiagent.utils.logger import get_logger

logger = get_logger(__name__)

def get_admin_service(db: Session = Depends(get_db)) -> AdminService:
    """
    Admin Service 의존성
    데이터베이스 세션을 주입받아 AdminService 인스턴스를 생성
    """
    try:
        return AdminService(db)
    except Exception as e:
        logger.error(f"Admin Service 생성 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서비스 초기화에 실패했습니다"
        )

def get_ml_data_service(db: Session = Depends(get_db)) -> MLDataService:
    """
    ML Data Service 의존성
    데이터베이스 세션을 주입받아 MLDataService 인스턴스를 생성
    """
    try:
        return MLDataService(db)
    except Exception as e:
        logger.error(f"ML Data Service 생성 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서비스 초기화에 실패했습니다"
        )

def verify_database_connection():
    """
    데이터베이스 연결 상태 확인 의존성
    헬스체크나 중요한 API에서 사용
    """
    try:
        if not check_db_connection():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="데이터베이스 연결이 불가능합니다"
            )
    except Exception as e:
        logger.error(f"데이터베이스 연결 확인 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="데이터베이스 상태를 확인할 수 없습니다"
        )

# API 키 인증 (선택적 - 나중에 구현 가능)
def verify_api_key(api_key: str = None) -> bool:
    """
    API 키 검증 (향후 보안 강화 시 사용)
    현재는 기본적으로 True 반환
    """
    # TODO: 실제 API 키 검증 로직 구현
    return True 