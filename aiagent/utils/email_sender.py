import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from .logger import get_logger

logger = get_logger('aiagent.utils.email_sender')

class EmailSender:
    def __init__(self):
        # 환경 변수에서 설정 로드
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.sender_email = os.getenv("SENDER_EMAIL")
        self.admin_email = os.getenv("ADMIN_EMAIL")

        if not all([self.smtp_user, self.smtp_password, self.sender_email, self.admin_email]):
            logger.warning("이메일 설정이 완료되지 않았습니다")
            self.is_configured = False
        else:
            self.is_configured = True

    def send_error_notification(self, error_data: dict) -> bool:
        """
        오류 발생 시 관리자에게 이메일 발송
        
        Args:
            error_data: 오류 정보를 담은 딕셔너리
                - client_id: 클라이언트 ID
                - transaction_id: 트랜잭션 ID
                - error_message: 오류 메시지
                - raw_data: 원본 데이터
        """
        if not self.is_configured:
            logger.error("이메일 설정이 되어있지 않아 발송할 수 없습니다")
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.admin_email
            msg['Subject'] = f"[영수증 파싱 오류] Client: {error_data['client_id']}"

            body = f"""
            영수증 파싱 중 오류가 발생했습니다.

            클라이언트 ID: {error_data['client_id']}
            트랜잭션 ID: {error_data['transaction_id']}
            오류 메시지: {error_data['error_message']}

            원본 데이터:
            {error_data['raw_data']}
            """

            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"오류 알림 이메일 발송 완료: {error_data['client_id']}")
            return True

        except Exception as e:
            logger.error(f"이메일 발송 실패: {str(e)}")
            return False

# 싱글톤 인스턴스 생성
email_sender = EmailSender() 