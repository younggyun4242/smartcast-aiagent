#!/usr/bin/env python3
"""
시간대 설정 테스트 스크립트
"""

import os
import time
from datetime import datetime
import pytz
from aiagent.utils.logger import get_logger

# 로거 가져오기
logger = get_logger('test_timezone')

def test_timezone():
    """시간대 설정 테스트"""
    
    print("=== 시간대 설정 테스트 ===")
    
    # 환경 변수 확인
    tz_env = os.environ.get('TZ', 'Not Set')
    print(f"TZ 환경 변수: {tz_env}")
    
    # 시스템 시간
    system_time = datetime.now()
    print(f"시스템 시간: {system_time}")
    
    # UTC 시간
    utc_time = datetime.utcnow()
    print(f"UTC 시간: {utc_time}")
    
    # 한국 시간 (pytz 사용)
    kst = pytz.timezone('Asia/Seoul')
    korea_time = datetime.now(kst)
    print(f"한국 시간 (pytz): {korea_time}")
    
    # 로거 테스트
    print("\n=== 로거 시간 테스트 ===")
    logger.info("한국 시간대로 로그 기록 테스트")
    logger.debug("디버그 메시지 - 시간 확인")
    logger.warning("경고 메시지 - 시간 확인")
    
    # 타임스탬프 비교
    print(f"\n=== 타임스탬프 비교 ===")
    print(f"현재 타임스탬프: {time.time()}")
    print(f"현재 시간 (로컬): {time.ctime()}")
    
    # Docker 환경에서의 시간대 확인
    try:
        with open('/etc/timezone', 'r') as f:
            container_tz = f.read().strip()
        print(f"컨테이너 시간대 (/etc/timezone): {container_tz}")
    except FileNotFoundError:
        print("컨테이너 시간대 파일 없음 (Docker 외부 환경)")
    
    try:
        # localtime 링크 확인
        import subprocess
        result = subprocess.run(['ls', '-la', '/etc/localtime'], 
                              capture_output=True, text=True)
        print(f"localtime 링크: {result.stdout.strip()}")
    except:
        print("localtime 링크 정보 확인 불가")

if __name__ == "__main__":
    test_timezone() 