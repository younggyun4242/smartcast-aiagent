import uvicorn
from fastapi import FastAPI
import threading
from aiagent.core.broker import main as broker_main
from aiagent.db.core import Base, engine
import logging
import logging.handlers
import os
import sys
import codecs
from aiagent.utils.logger import setup_logger, get_logger

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

# DB 테이블 생성
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Agent Server", 
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 브로커 연결 시작"""
    logger.info("서버 시작")
    # 브로커 연결을 별도 스레드로 실행
    threading.Thread(target=broker_main, daemon=True).start()

@app.get("/")
async def root():
    return {"status": "running"}

if __name__ == "__main__":
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_config=None  # uvicorn 기본 로깅 설정 비활성화
    )
