import logging
import sys
import threading
import os
from datetime import datetime
import pytz

# 로거 설정 완료 여부를 추적하는 플래그
_logger_configured = False
_lock = threading.Lock()

# 한국 시간대 설정
KST = pytz.timezone('Asia/Seoul')

class KSTFormatter(logging.Formatter):
    """한국 시간대를 사용하는 로그 포맷터"""
    
    def formatTime(self, record, datefmt=None):
        """로그 레코드의 시간을 한국 시간대로 변환"""
        # UTC 시간을 한국 시간으로 변환
        dt = datetime.fromtimestamp(record.created, tz=KST)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.strftime('%Y-%m-%d %H:%M:%S')

def setup_logger():
    """
    애플리케이션 전체에서 사용할 로거를 설정합니다.
    중복 호출을 방지하여 핸들러가 여러 번 추가되지 않도록 합니다.
    """
    global _logger_configured
    
    with _lock:
        # 이미 설정되었으면 중복 설정 방지
        if _logger_configured:
            return logging.getLogger()
        
        # 시스템 시간대를 한국으로 설정 (환경 변수 기반)
        if 'TZ' not in os.environ:
            os.environ['TZ'] = 'Asia/Seoul'
        
        # 루트 로거 설정
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # 기존 핸들러 제거
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 콘솔 핸들러 설정
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        
        # 한국 시간대를 사용하는 포맷터 설정
        formatter = KSTFormatter(
            '%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        # 루트 로거에만 핸들러 추가
        root_logger.addHandler(console_handler)
        
        # aiagent 네임스페이스 로거들의 propagate 설정
        # 이렇게 하면 자식 로거들이 루트 로거로 메시지를 전파하여 한 번만 출력됩니다
        aiagent_logger = logging.getLogger('aiagent')
        aiagent_logger.propagate = True  # 루트 로거로 전파
        
        _logger_configured = True
        return root_logger

def get_logger(name: str) -> logging.Logger:
    """
    로거를 가져옵니다. 필요시 자동으로 설정을 초기화합니다.
    
    Args:
        name: 로거 이름
        
    Returns:
        설정된 로거 인스턴스
    """
    # 로거가 아직 설정되지 않았으면 설정
    if not _logger_configured:
        setup_logger()
    
    logger = logging.getLogger(name)
    # 추가 핸들러 설정 없이 propagate로 처리
    logger.propagate = True
    return logger 