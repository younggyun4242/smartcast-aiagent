import zmq
import os
import json
import time
import signal
import sys
import threading
import traceback
from contextlib import contextmanager
from .protocol import MessageFormat, MessageType, ErrorCode
from ..services.processor import bill_processor, ProcessingError, BillProcessor
from ..utils.logger import get_logger

logger = get_logger('aiagent.core.broker')

# 환경변수 기반 설정
BROKER_HOST = os.getenv("BROKER_HOST", "localhost")
BROKER_PORT = os.getenv("BROKER_PORT", "5555")
CLIENT_ID = os.getenv("CLIENT_ID", "AIAGENT")
RECONNECT_TIMEOUT = 5  # 재연결 대기 시간 (초)
REGISTRATION_TIMEOUT = 3  # 등록 응답 대기 시간 (초)

# 종료 플래그
running = True

def signal_handler(signum, frame):
    """시그널 핸들러로 프로그램 종료 처리"""
    global running
    logger.info("프로그램 종료 신호를 받았습니다...")
    running = False

# 시그널 핸들러 등록 (Ctrl+C)
signal.signal(signal.SIGINT, signal_handler)

@contextmanager
def zmq_connection():
    """ZMQ 연결 컨텍스트 매니저"""
    ctx = zmq.Context()
    sock = None
    try:
        sock = ctx.socket(zmq.DEALER)
        sock.setsockopt(zmq.IDENTITY, CLIENT_ID.encode())
        sock.setsockopt(zmq.RECONNECT_IVL, 1000)  # 1초 후 재연결 시도
        sock.setsockopt(zmq.RECONNECT_IVL_MAX, 5000)  # 최대 5초 간격으로 재연결
        sock.setsockopt(zmq.LINGER, 0)  # 종료 시 메시지 즉시 폐기
        yield sock
    finally:
        if sock:
            sock.close()
        ctx.term()

def register_with_broker(sock):
    """브로커 등록 및 응답 대기"""
    attempt = 1
    while running:  # running 플래그를 사용하여 프로그램 종료 시 중단
        try:
            logger.info(f"브로커 등록 시도 (시도 #{attempt}) - Client ID: {CLIENT_ID}")
            # 프로토콜 정의를 사용한 등록 메시지 생성
            sock.send_multipart([b'', b"REGISTER", CLIENT_ID.encode(), b"", b""])
            logger.info("브로커에 등록 요청 전송 완료")

            # 등록 응답 대기
            start = time.time()
            while time.time() - start < REGISTRATION_TIMEOUT:
                if sock.poll(1000, zmq.POLLIN):
                    parts = sock.recv_multipart()
                    logger.info(f"브로커로부터 응답 수신: {[p.decode() if isinstance(p, bytes) else p for p in parts]}")
                    if parts[0] == b'':
                        parts = parts[1:]
                    if parts[0] == MessageType.OK:
                        logger.info(f"브로커 등록 성공 - Client ID: {CLIENT_ID}")
                        return True
                    else:
                        logger.warning(f"예상치 못한 응답 - Response: {parts}")
            logger.error(f"브로커 등록 타임아웃 - Client ID: {CLIENT_ID}")
            
        except Exception as e:
            logger.error(f"등록 중 예외 발생 - Client ID: {CLIENT_ID}, Error: {e}")
        
        # 재시도 전 대기
        wait_time = min(RECONNECT_TIMEOUT * attempt, 60)  # 최대 60초까지 대기
        logger.info(f"{wait_time}초 후 재시도합니다...")
        time.sleep(wait_time)
        attempt += 1
    
    return False

def handle_heartbeat(sock, parts):
    """HEARTBEAT 메시지 처리"""
    try:
        if len(parts) < 2:
            return
        client_id = parts[1]
        sock.send_multipart([b'', MessageType.PONG, client_id])
        logger.debug(f"PONG sent to {client_id.decode()}")
    except Exception as e:
        logger.error(f"Heartbeat 처리 중 오류: {e}")

def handle_ai_generate(sock, parts):
    """AI_GENERATE 메시지 처리"""
    try:
        if len(parts) < 3:
            logger.warning(f"AI_GENERATE 메시지 형식 오류: {parts}")
            return

        client_id = parts[1].decode()
        
        if not bill_processor:
            logger.error("영수증 처리기가 초기화되지 않았습니다")
            return
            
        try:
            # 처리 및 검증 수행
            result = bill_processor.process_ai_generate(client_id=client_id, raw_data=parts[2])
            
            # 검증이 성공한 경우에만 AI_OK 응답 전송
            if result.get("status") == "ok":
                # protocol.py 문서에 맞는 응답 형식으로 변환
                response_data = {
                    "status": "success",
                    "data": {
                        "xml_rule": result["rule_xml"],
                        "version": result["version"]
                    },
                    "version": "1.0"
                }
                sock.send_multipart([b'', MessageType.AI_OK, client_id.encode(), json.dumps(response_data).encode()])
                logger.info(f"AI_GENERATE 응답 전송 완료: {client_id}")
            else:
                # 검증 실패 시 에러 응답 전송
                error_result = {
                    "status": "error",
                    "error": result.get("error", "알 수 없는 오류가 발생했습니다")
                }
                sock.send_multipart([b'', MessageType.AI_ERROR, client_id.encode(), json.dumps(error_result).encode()])
                logger.error(f"AI_GENERATE 검증 실패: {client_id}")
            
        except ProcessingError as e:
            error_result = {
                "status": "error",
                "error": str(e)
            }
            sock.send_multipart([b'', MessageType.AI_ERROR, client_id.encode(), json.dumps(error_result).encode()])
            logger.error(f"AI_GENERATE 처리 오류: {client_id} - {str(e)}")
            
    except Exception as e:
        logger.error(f"AI_GENERATE 처리 중 예외 발생: {e}")
        try:
            error_result = {
                "status": "error",
                "error": f"내부 서버 오류: {str(e)}"
            }
            sock.send_multipart([b'', MessageType.AI_ERROR, client_id.encode(), json.dumps(error_result).encode()])
        except:
            logger.error("오류 응답 전송 실패")

def handle_ai_merge(sock, parts):
    """AI_MERGE 메시지 처리"""
    try:
        if len(parts) < 3:
            logger.warning(f"AI_MERGE 메시지 형식 오류: {parts}")
            return

        client_id = parts[1].decode()
        
        if not bill_processor:
            logger.error("영수증 처리기가 초기화되지 않았습니다")
            return
            
        try:
            result = bill_processor.process_ai_merge(client_id=client_id, raw_data=parts[2])
            
            if result.get("status") == "ok":
                # protocol.py 문서에 맞는 응답 형식으로 변환
                response_data = {
                    "status": "success",
                    "data": {
                        "merged_xml": result["merged_rule_xml"],
                        "changes": result["changes"],
                        "new_version": result["version"]
                    },
                    "version": "1.0"
                }
                sock.send_multipart([b'', MessageType.AI_OK, client_id.encode(), json.dumps(response_data).encode()])
                logger.info(f"AI_MERGE 응답 전송 완료: {client_id}")
            else:
                error_result = {
                    "status": "error",
                    "error": result.get("error", "알 수 없는 오류가 발생했습니다")
                }
                sock.send_multipart([b'', MessageType.AI_ERROR, client_id.encode(), json.dumps(error_result).encode()])
                logger.error(f"AI_MERGE 검증 실패: {client_id}")
        except ProcessingError as e:
            result = {
                "status": "error",
                "error": str(e)
            }
            sock.send_multipart([b'', MessageType.AI_ERROR, client_id.encode(), json.dumps(result).encode()])
            
    except Exception as e:
        logger.error(f"AI_MERGE 처리 중 예외 발생: {e}")

def message_loop(sock):
    """메시지 수신 루프"""
    logger.info("메시지 수신 루프 시작")
    while running:
        try:
            if sock.poll(1000, zmq.POLLIN) == 0:
                continue  # 타임아웃

            parts = sock.recv_multipart()
            if parts[0] == b'':
                parts = parts[1:]
            
            cmd = parts[0]
            if cmd == MessageType.PING:
                handle_heartbeat(sock, parts)
            elif cmd == MessageType.AI_GENERATE:
                handle_ai_generate(sock, parts)
            elif cmd == MessageType.AI_MERGE:
                handle_ai_merge(sock, parts)
            else:
                logger.info(f"기타 메시지 수신: {parts}")

        except zmq.ZMQError as e:
            if e.errno == zmq.ETERM:
                logger.error("ZMQ 컨텍스트가 종료됨")
                break
            logger.error(f"ZMQ 오류 발생: {e}")
        except Exception as e:
            logger.error(f"메시지 수신 중 예외 발생: {e}", exc_info=True)

    logger.info("메시지 수신 루프 종료")

def main():
    """메인 실행 함수"""
    consecutive_failures = 0
    while running:
        try:
            with zmq_connection() as sock:
                logger.info(f"브로커({BROKER_HOST}:{BROKER_PORT})에 연결 시도")
                sock.connect(f"tcp://{BROKER_HOST}:{BROKER_PORT}")
                
                if not register_with_broker(sock):
                    logger.error("브로커 등록 실패")
                    continue

                consecutive_failures = 0  # 성공하면 실패 카운트 초기화
                message_loop(sock)
                
        except Exception as e:
            logger.error(f"예상치 못한 오류 발생: {e}", exc_info=True)
            consecutive_failures += 1
            wait_time = min(RECONNECT_TIMEOUT * consecutive_failures, 60)
            logger.info(f"{wait_time}초 후 재시도합니다...")
            time.sleep(wait_time)

if __name__ == "__main__":
    main()
