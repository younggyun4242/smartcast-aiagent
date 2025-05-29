FROM python:3.11-slim

# 작업 디렉토리 지정
WORKDIR /aiagent

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 복사
COPY . .

# 환경 변수
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/aiagent/aiagent

# FastAPI 실행 (모니터링용)
CMD ["uvicorn", "aiagent.main:app", "--host", "0.0.0.0", "--port", "8000"]

