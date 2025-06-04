"""
PostgreSQL 데이터베이스 연결 및 설정 모듈
PostgreSQL 전용 (SQLite 제거됨)
"""

import os
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from aiagent.utils.logger import get_logger

logger = get_logger(__name__)

# 환경 변수에서 PostgreSQL URL 가져오기
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://aiagent:password@localhost:5432/aiagent_db")

# PostgreSQL 확인
if not DATABASE_URL.startswith("postgresql://"):
    raise ValueError("PostgreSQL DATABASE_URL이 필요합니다. 환경 변수를 확인하세요.")

# PostgreSQL 엔진 설정
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,  # 연결 상태 확인
    echo=False  # 프로덕션에서는 False
)

# 연결 정보 로깅 (보안을 위해 비밀번호 숨김)
db_info = DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'localhost'
logger.info(f"PostgreSQL 데이터베이스에 연결: {db_info}")

# 세션 메이커
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스 (모든 모델의 부모 클래스)
Base = declarative_base()

# 메타데이터
metadata = MetaData()

def get_db():
    """
    데이터베이스 세션을 제공하는 의존성 함수
    FastAPI의 Dependency Injection에서 사용
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """
    모든 테이블 생성
    애플리케이션 시작 시 호출
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("PostgreSQL 테이블이 성공적으로 생성되었습니다.")
    except Exception as e:
        logger.error(f"PostgreSQL 테이블 생성 중 오류 발생: {e}")
        raise

def drop_tables():
    """
    모든 테이블 삭제 (개발/테스트용)
    """
    try:
        Base.metadata.drop_all(bind=engine)
        logger.warning("모든 PostgreSQL 테이블이 삭제되었습니다.")
    except Exception as e:
        logger.error(f"PostgreSQL 테이블 삭제 중 오류 발생: {e}")
        raise

def check_db_connection():
    """
    PostgreSQL 연결 상태 확인
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("PostgreSQL 연결 상태가 정상입니다.")
        return True
    except Exception as e:
        logger.error(f"PostgreSQL 연결 실패: {e}")
        return False 