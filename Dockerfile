FROM python:3.11-slim

# 시간대 패키지 설치 및 한국 시간대 설정
RUN apt-get update && apt-get install -y tzdata && \
    ln -sf /usr/share/zoneinfo/Asia/Seoul /etc/localtime && \
    echo "Asia/Seoul" > /etc/timezone && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 지정
WORKDIR /app

# 의존성 먼저 복사 및 설치 (Docker 캐시 최적화)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 필요한 소스만 선택적 복사 (더 정확한 방법)
COPY aiagent/ ./aiagent/
COPY *.py ./

# 환경 변수
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV TZ=Asia/Seoul
ENV LOG_LEVEL=INFO

EXPOSE 5000

CMD ["python", "-m", "aiagent.main"]

