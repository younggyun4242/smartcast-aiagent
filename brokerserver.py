#!/usr/bin/env python3
"""
AI AGENT ZeroMQ 브로커
"""
import os
import sys
import logging
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가 (여러 방법 시도)
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Docker 환경을 고려한 추가 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, '..'))

# aiagent 모듈 import 시도
try:
    from aiagent.utils.logger import setup_logger, get_logger
    USE_CUSTOM_LOGGER = True
except ImportError:
    # aiagent 모듈을 찾을 수 없는 경우 기본 로깅 사용
    USE_CUSTOM_LOGGER = False
    print("WARNING: aiagent 모듈을 찾을 수 없습니다. 기본 로깅을 사용합니다.")

import zmq
import time
import threading
import re
import signal
from logging.handlers import TimedRotatingFileHandler
from zmq.utils.monitor import recv_monitor_message

last_active = time.monotonic()  # 메시지 수신 시각 갱신

ZMQ_EVENT_MAP = {
    zmq.EVENT_CONNECTED: "CONNECTED",
    zmq.EVENT_CONNECT_DELAYED: "CONNECT_DELAYED",
    zmq.EVENT_CONNECT_RETRIED: "CONNECT_RETRIED",
    zmq.EVENT_LISTENING: "LISTENING",
    zmq.EVENT_BIND_FAILED: "BIND_FAILED",
    zmq.EVENT_ACCEPTED: "ACCEPTED",
    zmq.EVENT_ACCEPT_FAILED: "ACCEPT_FAILED",
    zmq.EVENT_CLOSED: "CLOSED",
    zmq.EVENT_CLOSE_FAILED: "CLOSE_FAILED",
    zmq.EVENT_DISCONNECTED: "DISCONNECTED",
    # ... 필요시 추가
}

# 로거 설정
if USE_CUSTOM_LOGGER:
    # 통합 로거 설정
    setup_logger()
    logger = get_logger("broker")
else:
    # 기본 로깅 설정
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s][%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger("broker")

# 파일 로거 추가 (broker 전용)
broker_file_handler = TimedRotatingFileHandler("broker.log", when="midnight", backupCount=15, encoding="utf-8")
broker_file_handler.setLevel(logging.DEBUG)
broker_formatter = logging.Formatter(
    '[%(asctime)s][%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
broker_file_handler.setFormatter(broker_formatter)
logger.addHandler(broker_file_handler)

def start_monitor(sock: zmq.Socket, name: str):
    """
    주어진 소켓에서 EVENT_ALL 모니터를 시작하고,
    발생하는 이벤트를 로그로 출력하는 스레드 함수를 리턴합니다.
    """
    monitor = sock.get_monitor_socket()  # EVENT_ALL 기본
    def _run():
        while True:
            try:
                evt = recv_monitor_message(monitor)
            except zmq.ContextTerminated:
                break
            etype = evt['event']
            etype_name = ZMQ_EVENT_MAP.get(etype, str(etype))
            endpoint = evt.get('endpoint', b'').decode()
            logger.info(f"[MONITOR:{name}] event={etype_name} endpoint={endpoint}")
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t

def broker():
    # clients, p2p_info = load_clients_from_db(DB_PATH)  # 삭제
    clients = {}
    p2p_info = {}
    logger.info(f"브로커 시작: 클라이언트 정보 메모리에서만 관리")
    logger.error(f"브로커 시작: 클라이언트 정보 메모리에서만 관리")

    ctx = zmq.Context()
    socket = ctx.socket(zmq.ROUTER)
    socket.bind("tcp://*:5555")
    id_pattern = re.compile(r"^[A-Z]{6}$")  # 6자리 허용

    global last_active
    while True:
        msg = socket.recv_multipart()
        last_active = time.monotonic()  # 메시지 수신 시각 갱신
        if len(msg) < 3:
            logger.warning(f"잘못된 프레임 수신: {msg}")
            continue
        client_rid, empty, cmd, *args = msg
        logger.debug(f"수신: {msg}")

        # 클라이언트 ID가 등록되어 있는지 확인 (REGISTER, GET_ADDR 명령은 제외)
        if cmd not in (b"REGISTER", b"GET_ADDR"):
            if not any(v == client_rid for v in clients.values()):
                logger.warning(f"미등록 클라이언트: {client_rid}")
                socket.send_multipart([client_rid, b"", b"ERROR", b"Registration required"])
                continue

        if cmd == b"REGISTER":
            my_id = args[0].decode()
            my_ip = args[1].decode() if len(args) > 1 else ""
            my_port = args[2].decode() if len(args) > 2 else ""
            if not id_pattern.match(my_id):
                logger.info(f"잘못된 ID 등록 시도: {my_id}")
                socket.send_multipart([client_rid, b"", b"ERROR", b"Invalid ID"])
                continue
            prev_rid = clients.get(my_id)
            if prev_rid is not None and prev_rid != client_rid:
                logger.info(f"{my_id}의 routing_id 갱신: {prev_rid} → {client_rid}")
            clients[my_id] = client_rid  # routing_id는 메모리에서만 관리
            p2p_info[my_id] = (my_ip, my_port)
            logger.info(f"등록(갱신) 완료: {my_id}, ip={my_ip}, port={my_port}")
            socket.send_multipart([client_rid, b"", b"OK"])
            continue

        elif cmd == b"GET_ADDR":
            target_id = args[0].decode()
            if target_id in p2p_info:
                ip, port = p2p_info[target_id]
                logger.info(f"GET_ADDR: {target_id} → ip={ip}, port={port}")
                socket.send_multipart([client_rid, b"", b"ADDR", target_id.encode(), ip.encode(), port.encode()])
            else:
                logger.info(f"GET_ADDR: {target_id} 정보 없음")
                socket.send_multipart([client_rid, b"", b"ERROR", b"Unknown target"])
            continue

        elif cmd == b"BILL_SEND":
            # [client_rid, b'', b'BILL_SEND', dest_id, ...payload]
            if len(args) < 1:
                logger.warning(f"BILL_SEND: 목적지 ID 누락: {msg}")
                socket.send_multipart([client_rid, b"", b"ERROR", b"Bad destination ID"])
                continue
            dest_id = args[0].decode()
            payload = args[1:]
            if not id_pattern.match(dest_id):
                logger.info(f"BILL_SEND: 잘못된 목적지 ID: {dest_id}")
                socket.send_multipart([client_rid, b"", b"ERROR", b"Bad destination ID"])
                continue
            if dest_id not in clients:
                logger.info(f"BILL_SEND: 미등록 목적지: {dest_id}")
                socket.send_multipart([client_rid, b"", b"ERROR", b"Unknown destination"])
                continue
            from_id = next(k for k, v in clients.items() if v == client_rid).encode()
            dest_rid = clients[dest_id]
            logger.info(f"BILL_SEND 전달: {from_id.decode()} → {dest_id}, payload={payload}")
            socket.send_multipart([
                dest_rid, b"",
                b"BILL_SEND", from_id, *payload
            ])
            continue

        elif cmd == b"BILL_OK":
            # [client_rid, b'', b'BILL_OK', dest_id, bill_no, ...]
            logger.debug(f"BILL_OK 수신 프레임: {msg}")
            if len(args) < 1:
                logger.warning(f"BILL_OK: 목적지 ID 누락: {msg}")
                continue
            dest_id = args[0].decode()
            payload = args[1:]  # bill_no 등 추가 payload
            if not id_pattern.match(dest_id):
                logger.info(f"BILL_OK: 잘못된 목적지 ID: {dest_id}")
                continue
            if dest_id not in clients:
                logger.info(f"BILL_OK: 미등록 목적지: {dest_id}")
                continue
            from_id = next(k for k, v in clients.items() if v == client_rid).encode()
            dest_rid = clients[dest_id]
            # bill_no 값만 명확하게 로그에 남김
            bill_no_str = payload[0].decode(errors='replace') if payload else ''
            logger.info(f"BILL_OK 전달: {from_id.decode()} → {dest_id}, bill_no={bill_no_str}, raw_payload={payload}")
            send_frame = [dest_rid, b"", b"BILL_OK", from_id, *payload]
            logger.debug(f"BILL_OK 송신 프레임: {send_frame}")
            socket.send_multipart(send_frame)
            continue

        elif cmd == b"AI_GENERATE":
            # [client_rid, b'', b'AI_GENERATE', dest_id, json_data]
            if len(args) < 2:
                logger.warning(f"AI_GENERATE: 잘못된 형식: {msg}")
                socket.send_multipart([client_rid, b"", b"ERROR", b"Invalid AI_GENERATE format"])
                continue
                
            dest_id = args[0].decode()
            payload = args[1:]
            
            if not id_pattern.match(dest_id):
                logger.info(f"AI_GENERATE: 잘못된 목적지 ID: {dest_id}")
                socket.send_multipart([client_rid, b"", b"ERROR", b"Bad destination ID"])
                continue
                
            if dest_id not in clients:
                logger.info(f"AI_GENERATE: 미등록 목적지: {dest_id}")
                socket.send_multipart([client_rid, b"", b"ERROR", b"Unknown destination"])
                continue
                
            from_id = next(k for k, v in clients.items() if v == client_rid).encode()
            dest_rid = clients[dest_id]
            logger.info(f"AI_GENERATE 전달: {from_id.decode()} → {dest_id}")
            
            socket.send_multipart([
                dest_rid, b"",
                b"AI_GENERATE", from_id, *payload
            ])
            continue

        elif cmd == b"AI_MERGE":
            # [client_rid, b'', b'AI_MERGE', dest_id, json_data]
            if len(args) < 2:
                logger.warning(f"AI_MERGE: 잘못된 형식: {msg}")
                socket.send_multipart([client_rid, b"", b"ERROR", b"Invalid AI_MERGE format"])
                continue
                
            dest_id = args[0].decode()
            payload = args[1:]
            
            if not id_pattern.match(dest_id):
                logger.info(f"AI_MERGE: 잘못된 목적지 ID: {dest_id}")
                socket.send_multipart([client_rid, b"", b"ERROR", b"Bad destination ID"])
                continue
                
            if dest_id not in clients:
                logger.info(f"AI_MERGE: 미등록 목적지: {dest_id}")
                socket.send_multipart([client_rid, b"", b"ERROR", b"Unknown destination"])
                continue
                
            from_id = next(k for k, v in clients.items() if v == client_rid).encode()
            dest_rid = clients[dest_id]
            logger.info(f"AI_MERGE 전달: {from_id.decode()} → {dest_id}")
            
            socket.send_multipart([
                dest_rid, b"",
                b"AI_MERGE", from_id, *payload
            ])
            continue

        elif cmd == b"AI_OK":
            # [client_rid, b'', b'AI_OK', dest_id, response_data]
            if len(args) < 2:
                logger.warning(f"AI_OK: 잘못된 형식: {msg}")
                continue
                
            dest_id = args[0].decode()
            payload = args[1:]
            
            if not id_pattern.match(dest_id):
                logger.info(f"AI_OK: 잘못된 목적지 ID: {dest_id}")
                continue
                
            if dest_id not in clients:
                logger.info(f"AI_OK: 미등록 목적지: {dest_id}")
                continue
                
            from_id = next(k for k, v in clients.items() if v == client_rid).encode()
            dest_rid = clients[dest_id]
            logger.info(f"AI_OK 전달: {from_id.decode()} → {dest_id}")
            
            socket.send_multipart([
                dest_rid, b"",
                b"AI_OK", from_id, *payload
            ])
            continue

        elif cmd == b"AI_ERROR":
            # [client_rid, b'', b'AI_ERROR', dest_id, error_data]
            if len(args) < 2:
                logger.warning(f"AI_ERROR: 잘못된 형식: {msg}")
                continue
                
            dest_id = args[0].decode()
            payload = args[1:]
            
            if not id_pattern.match(dest_id):
                logger.info(f"AI_ERROR: 잘못된 목적지 ID: {dest_id}")
                continue
                
            if dest_id not in clients:
                logger.info(f"AI_ERROR: 미등록 목적지: {dest_id}")
                continue
                
            from_id = next(k for k, v in clients.items() if v == client_rid).encode()
            dest_rid = clients[dest_id]
            logger.info(f"AI_ERROR 전달: {from_id.decode()} → {dest_id}")
            
            socket.send_multipart([
                dest_rid, b"",
                b"AI_ERROR", from_id, *payload
            ])
            continue

        elif cmd == b"PING":
            # PING 메시지 처리: [client_rid, b'', b'PING', from_id, target_id1, target_id2, ...]
            if len(args) < 2:
                logger.warning(f"잘못된 PING 형식: {msg}")
                socket.send_multipart([client_rid, b"", b"ERROR", b"Invalid PING format"])
                continue

            sender_id = args[0].decode()  # 원래 발신자 ID
            target_ids = [arg.decode() for arg in args[1:]]  # 목적지 ID 목록

            # target_ids가 비어있거나, from_id와 target_id[0]이 같으면 바로 PONG 응답
            if not target_ids or sender_id == target_ids[0]:
                if sender_id in clients:
                    from_rid = clients[sender_id]
                    logger.info(f"PING to BROKER: {sender_id}에게 PONG 응답")
                    socket.send_multipart([
                        from_rid, b"",
                        b"PONG", from_rid, b"", b""
                    ])
                continue

            logger.info(f"PING 요청: {sender_id} → {target_ids}")

            # 각 목적지 ID에 대해 PING 전송
            for target_id in target_ids:
                # 목적지 ID가 유효한지 확인
                if not id_pattern.match(target_id):
                    logger.info(f"PING: 잘못된 목적지 ID: {target_id}")
                    socket.send_multipart([client_rid, b"", b"ERROR", b"Bad target ID: " + target_id.encode()])
                    continue

                # 목적지 ID가 등록되어 있는지 확인
                if target_id not in clients:
                    logger.info(f"PING: 미등록 목적지: {target_id}")
                    socket.send_multipart([client_rid, b"", b"ERROR", b"Unknown target: " + target_id.encode()])
                    continue

                target_rid = clients[target_id]
                logger.info(f"PING 전달: {sender_id} → {target_id} (routing_id={target_rid})")

                # 목적지에 PING 메시지 전송 (routing_id를 정확히 사용)
                # 프레임: [routing_id, b'', b'PING', sender_id]
                socket.send_multipart([
                    target_rid, b"",
                    b"PING", sender_id.encode()
                ])

            # 목적지로부터 PONG 응답을 기다림 (비동기적으로 처리됨)
            continue

        elif cmd == b"PONG":
            # PONG 메시지 처리: [client_rid, b'', b'PONG', target_id]
            if len(args) < 1:
                logger.warning(f"잘못된 PONG 형식: {msg}")
                continue

            target_id = args[0].decode()  # PONG 응답을 받을 대상 ID

            # 응답 대상 ID가 유효한지 확인
            if not id_pattern.match(target_id):
                logger.info(f"PONG: 잘못된 목적지 ID: {target_id}")
                continue

            # 응답 대상 ID가 등록되어 있는지 확인
            if target_id not in clients:
                logger.info(f"PONG: 미등록 목적지: {target_id}")
                continue

            from_id = next(k for k, v in clients.items() if v == client_rid)
            target_rid = clients[target_id]

            # 원래 발신자에게 PONG 응답 전달 (누구로부터 온 응답인지 포함)
            ip, port = p2p_info.get(from_id, (b"", b""))
            if not isinstance(ip, bytes):
                ip = ip.encode()
            if not isinstance(port, bytes):
                port = port.encode()

            logger.info(f"PONG 전달: {from_id} {ip} {port} → {target_id}")

            socket.send_multipart([
                target_rid, b"",
                b"PONG", from_id.encode(), ip, port
            ])
            continue

        else:
            logger.warning(f"지원하지 않는 커맨드(무시): {cmd}")
            continue

def watchdog():
    """
    브로커의 활성 상태를 모니터링하는 워치독 스레드
    """
    global last_active
    while True:
        time.sleep(10)  # 10초마다 체크
        if time.monotonic() - last_active > 60:  # 1분 이상 메시지 없으면 경고
            logger.warning("1분 이상 메시지 수신 없음")
        else:
            logger.debug("브로커 정상 동작 중")

if __name__ == "__main__":
    # 워치독 스레드 시작
    watchdog_thread = threading.Thread(target=watchdog, daemon=True)
    watchdog_thread.start()
    
    # 브로커 시작
    broker()
