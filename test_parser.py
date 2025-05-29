#!/usr/bin/env python3
"""
파서 테스트 스크립트
"""

import os
import sys
import json
import time
import logging
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from aiagent.utils.logger import get_logger

logger = get_logger('test_parser')

import zmq
import uuid
import random
import string
import os

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def generate_valid_id():
    return ''.join(random.choices(string.ascii_uppercase, k=6))

# 기본 값 세팅
client_id = generate_valid_id()
transaction_id = str(uuid.uuid4())

# 브로커 서버 설정
BROKER_HOST = os.getenv("BROKER_HOST", "broker")  # Docker 서비스 이름 사용
BROKER_PORT = os.getenv("BROKER_PORT", "5555")

logger.info(f"🆔 클라이언트 ID: {client_id}")
logger.info(f"🔁 트랜잭션 ID: {transaction_id}")
logger.info(f"🔌 브로커 서버: {BROKER_HOST}:{BROKER_PORT}")

# ZMQ 설정
context = zmq.Context()
socket = context.socket(zmq.DEALER)
socket.setsockopt(zmq.IDENTITY, client_id.encode())
socket.connect(f"tcp://{BROKER_HOST}:{BROKER_PORT}")  # 환경변수 기반 연결

# 테스트용 영수증 JSON 구성 (hex 데이터 사용)
test_receipt = {
    "type": "xml",
    "mode": "GENERATE",
    "client_id": client_id,
    "transaction_id": transaction_id,
    "receipt_data": {
        "raw_data": "20202020201b21105ba2c2bdc5b1d42dc1d6b9e6c1d6b9aebcad5d2dc1d6b9e6311b21000d0a0a1b21100a5bc5d7c0ccbaed5d20b1e2babb2d313032205bbcd5b4d4bcf65d20303120b8ed0a5bc1d6b9aec0da5d20c0ccbcbcb5b9202020202020205bc1d6b9aeb9f8c8a35d20303131352d303030311b21000a3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d0a1b211020202020b8de2020b4ba2020b8ed2020202020202020202020202020202020bcf6b7ae202020b1b8bad00d0a2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d0d0ac2abbbcd20202020202020202020202020202020202020202020202020202020202031202020bdc5b1d40d0abdbab8b6c6ae2041bcbcc6ae2020202020202020202020202020202020202020202031202020bdc5b1d40d0aa2bac2fcc4a1b1e8b9e420202020202020202020202020202020202020202020202031202020bcb1c5c30d0aa2bab5c8c0e5c2eeb0b320202020202020202020202020202020202020202020202031202020bcb1c5c31b21000a2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d0a1b21100d0a5bc1d6b9e6b8deb8f05d201b21000a3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d0a504f533a30312020202020205bc1d6b9aebdc3b0a35d20323032352d30352d32322031343a32313a34320a0a0a0a0a0a1b69"
    },
    "version": "1.0"
}

# AI_MERGE 테스트용 데이터 (hex 데이터 사용)
test_merge = {
    "type": "xml",
    "mode": "MERGE",
    "client_id": client_id,
    "transaction_id": str(uuid.uuid4()),
    "receipt_data": {
        "raw_data": "20202020201b21105ba2bac3dfb0a12dc1d6b9e6c1d6b9aebcad5d2dc1d6b9e6311b21000d0a0a1b21100a5bc5d7c0ccbaed5d20b1e2babb2d313032205bbcd5b4d4bcf65d20303120b8ed0a5bc1d6b9aec0da5d20c0ccbcbcb5b9202020202020205bc1d6b9aeb9f8c8a35d20303131352d303030321b21000a3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d0a1b211020202020b8de2020b4ba2020b8ed2020202020202020202020202020202020bcf6b7ae202020b1b8bad00d0a2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d0d0ac2abbbcd20202020202020202020202020202020202020202020202020202020202d31202020c3ebbcd21b21000a2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d0a1b21100d0a5bc1d6b9e6b8deb8f05d201b21000a3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d0a504f533a30312020202020205bc1d6b9aebdc3b0a35d20323032352d30352d32322031343a32323a30310a0a0a0a0a0a1b69"
    },
    "current_xml": None,  # AI_GENERATE 응답에서 받은 XML을 여기에 설정
    "current_version": None,  # AI_GENERATE 응답에서 받은 버전을 여기에 설정
    "version": "1.0"
}

try:
    # 1. 등록
    logger.info("=== 등록 요청 전송 ===")
    # 등록 요청 형식: [empty, "REGISTER", my_id, my_ip, my_port]
    socket.send_multipart([
        b"",
        b"REGISTER",
        client_id.encode(),
        b"127.0.0.1",  # 테스트용 IP
        b"0"  # 테스트용 포트
    ])
    
    # 응답 대기 시간 설정
    if socket.poll(3000):  # 3초 대기
        register_resp = socket.recv_multipart()
        logger.info(f"REGISTER 응답: {[r.decode(errors='ignore') for r in register_resp]}")

        if len(register_resp) >= 2 and register_resp[1] == b"OK":
            logger.info("✅ 등록 성공")

            # 2. AI_GENERATE 테스트
            logger.info("\n=== 🤖 AI_GENERATE 테스트 시작 ===")
            destination_id = b"AIAGNT"
            message_json = json.dumps(test_receipt, ensure_ascii=False)
            encoded_message = message_json.encode("utf-8")

            logger.debug(f"[전송 구조] [b'', b'AI_GENERATE', {destination_id}, {len(encoded_message)} bytes]")
            logger.debug(f"[요청 본문]:\n{message_json}")

            socket.send_multipart([
                b"",
                b"AI_GENERATE",
                destination_id,
                encoded_message
            ])
            logger.info("📤 AI_GENERATE 요청 전송 완료")

            # AI_GENERATE 응답 수신
            if socket.poll(10000):  # 10초 대기
                response = socket.recv_multipart()
                logger.info(f"📥 응답 수신: {len(response)} 프레임")

                if len(response) >= 4:
                    if response[1] == b"AI_OK":
                        generate_result = json.loads(response[3].decode(errors='ignore'))
                        logger.info("✅ AI_GENERATE 성공")
                        logger.info("=== 생성 결과 ===")
                        logger.info(json.dumps(generate_result, indent=2, ensure_ascii=False))

                        # AI_MERGE 테스트 준비
                        test_merge["current_xml"] = generate_result["rule_xml"]
                        test_merge["current_version"] = generate_result["version"]

                        # 3. AI_MERGE 테스트
                        logger.info("\n=== 🔄 AI_MERGE 테스트 시작 ===")
                        merge_json = json.dumps(test_merge, ensure_ascii=False)
                        encoded_merge = merge_json.encode("utf-8")

                        logger.debug(f"[전송 구조] [b'', b'AI_MERGE', {destination_id}, {len(encoded_merge)} bytes]")
                        logger.debug(f"[요청 본문]:\n{merge_json}")

                        socket.send_multipart([
                            b"",
                            b"AI_MERGE",
                            destination_id,
                            encoded_merge
                        ])
                        logger.info("📤 AI_MERGE 요청 전송 완료")

                        # AI_MERGE 응답 수신
                        if socket.poll(10000):  # 10초 대기
                            merge_response = socket.recv_multipart()
                            logger.info(f"📥 응답 수신: {len(merge_response)} 프레임")

                            if len(merge_response) >= 4 and merge_response[1] == b"AI_OK":
                                merge_result = json.loads(merge_response[3].decode(errors='ignore'))
                                logger.info("✅ AI_MERGE 성공")
                                logger.info("=== 병합 결과 ===")
                                logger.info(json.dumps(merge_result, indent=2, ensure_ascii=False))
                            else:
                                logger.warning("❗ AI_MERGE 예상치 못한 응답 형식")
                                logger.warning(f"전체 응답: {[r.decode(errors='ignore') for r in merge_response]}")
                        else:
                            logger.error("❗ AI_MERGE 응답 타임아웃")
                    elif response[1] == b"AI_ERROR":
                        error_result = json.loads(response[3].decode(errors='ignore'))
                        logger.error("❌ AI_GENERATE 실패")
                        logger.error("=== 오류 내용 ===")
                        logger.error(json.dumps(error_result, indent=2, ensure_ascii=False))
                else:
                    logger.error("❌ 잘못된 응답 형식")
        else:
            logger.error("❌ 등록 실패")
            logger.error(f"응답 내용: {[r.decode(errors='ignore') for r in register_resp]}")
    else:
        logger.error("❌ 등록 응답 타임아웃")

except Exception as e:
    logger.exception(f"❗ 예외 발생: {str(e)}")

finally:
    logger.info("🔚 테스트 종료")
    socket.close()
    context.term()
