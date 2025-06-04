"""
AI Agent 메인 애플리케이션
기존 AI 파싱 서비스 + 새로운 관리자 페이지 API (PostgreSQL 통합)
"""

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status, Depends
import threading
from dotenv import load_dotenv
from aiagent.core.broker import main as broker_main
import logging
import logging.handlers
import os
import sys
import codecs
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

# 기존 imports
from aiagent.utils.logger import setup_logger, get_logger

# .env 파일 로드 (가장 먼저 실행되어야 함)
load_dotenv()

# PostgreSQL 통합 (SQLite 제거)
from aiagent.database import create_tables, check_db_connection

# 관리자 API imports
from aiagent.api.v1.admin.parsing_errors import router as parsing_errors_router
from aiagent.api.dependencies import verify_database_connection
from aiagent.exceptions import BaseAppException, NotFoundError, ValidationError, BusinessLogicError
from aiagent.api.v1.admin.schemas import ErrorResponse, HealthCheckResponse

# 로그 디렉토리 생성
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# 콘솔 출력 인코딩 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# 통합 로거 설정 (한 번만 호출)
setup_logger()

# 파일 핸들러 추가 (콘솔 핸들러는 setup_logger에서 설정됨)
root_logger = logging.getLogger()
file_handler = logging.handlers.TimedRotatingFileHandler(
    filename=os.path.join(log_dir, 'aiagent.log'),
    when='midnight',
    interval=1,
    backupCount=30,
    encoding='utf-8',
    errors='strict'
)
file_handler.setLevel(logging.DEBUG)

# 파일 핸들러 포맷 설정
log_formatter = logging.Formatter(
    fmt='%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(log_formatter)
root_logger.addHandler(file_handler)

# 메인 로거 가져오기
logger = get_logger('aiagent.main')
logger.debug("로깅 시스템 초기화 완료 - 한글 테스트")

app = FastAPI(
    title="AI Agent Server", 
    description="AI 파싱 서비스 + 관리자 페이지 API (PostgreSQL 통합)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === 글로벌 예외 핸들러 ===

@app.exception_handler(BaseAppException)
async def handle_app_exception(request: Request, exc: BaseAppException):
    """커스텀 애플리케이션 예외 핸들러"""
    logger.error(f"애플리케이션 예외 발생: {exc.message} (코드: {exc.error_code})")
    
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if isinstance(exc, NotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, ValidationError):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, BusinessLogicError):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error_code=exc.error_code,
            message=exc.message
        ).dict()
    )

@app.exception_handler(PydanticValidationError)
async def handle_validation_error(request: Request, exc: PydanticValidationError):
    """Pydantic 검증 오류 핸들러"""
    logger.warning(f"입력 데이터 검증 실패: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error_code="VALIDATION_ERROR",
            message="입력 데이터가 올바르지 않습니다",
            details=str(exc)
        ).dict()
    )

@app.exception_handler(Exception)
async def handle_general_exception(request: Request, exc: Exception):
    """일반 예외 핸들러"""
    logger.error(f"예상치 못한 오류 발생: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error_code="INTERNAL_SERVER_ERROR",
            message="서버 내부 오류가 발생했습니다"
        ).dict()
    )

# === 기본 엔드포인트 ===

@app.get("/")
async def root():
    """기존 루트 엔드포인트 - 호환성 유지"""
    return {"status": "running"}

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """시스템 헬스체크"""
    try:
        db_status = "connected" if check_db_connection() else "disconnected"
    except:
        db_status = "unknown"
    
    return HealthCheckResponse(
        timestamp=datetime.now().isoformat(),
        database=db_status
    )

# === API 라우터 등록 ===

# 관리자 API v1
app.include_router(
    parsing_errors_router,
    prefix="/api/v1/admin",
    tags=["관리자 API"]
)

# === 애플리케이션 이벤트 ===

@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행"""
    logger.info("AI Agent 애플리케이션 시작 (PostgreSQL 통합)")
    
    # PostgreSQL 데이터베이스 연결 확인 및 테이블 생성
    try:
        if check_db_connection():
            logger.info("PostgreSQL 데이터베이스 연결 성공")
            create_tables()
            logger.info("PostgreSQL 테이블 확인/생성 완료")
        else:
            logger.error("PostgreSQL 데이터베이스 연결 실패 - 애플리케이션이 제대로 작동하지 않을 수 있습니다")
            logger.error("환경 변수 DATABASE_URL을 확인하세요")
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        raise e
    
    # 기존 브로커 연결 시작 (별도 스레드)
    logger.info("브로커 연결을 시작합니다...")
    threading.Thread(target=broker_main, daemon=True).start()

@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 시 실행"""
    logger.info("AI Agent 애플리케이션 종료")

# === 미들웨어 ===

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """모든 HTTP 요청 로깅"""
    start_time = datetime.now()
    
    # 관리자 API 요청만 상세 로깅
    if request.url.path.startswith("/api/v1/admin"):
        logger.info(f"관리자 API 요청: {request.method} {request.url}")
    
    # 요청 처리
    response = await call_next(request)
    
    # 처리 시간 계산
    process_time = (datetime.now() - start_time).total_seconds()
    
    # 관리자 API 응답만 상세 로깅
    if request.url.path.startswith("/api/v1/admin"):
        logger.info(f"관리자 API 응답: {request.method} {request.url} - {response.status_code} ({process_time:.3f}s)")
    
    # 응답 헤더에 처리 시간 추가
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

if __name__ == "__main__":
    # 환경 변수에서 설정 읽기
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    logger.info(f"서버 시작: {host}:{port} (debug={debug})")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=debug,
        log_level="info",
        log_config=None  # uvicorn 기본 로깅 설정 비활성화 (기존 설정 유지)
    )
