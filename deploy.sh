#!/bin/bash

# SmartCast AI Agent 서버 배포 스크립트
# 사용법: ./deploy.sh [VERSION] [ENVIRONMENT]

VERSION=${1:-latest}
ENVIRONMENT=${2:-prod}
IMAGE_NAME="smartcast-aiagent"
REGISTRY="younggyun"  # 빌드 시와 동일하게 설정

echo "🚀 SmartCast AI Agent 서버 배포 시작..."
echo "📦 버전: ${VERSION}"
echo "🏭 환경: ${ENVIRONMENT}"

# 환경 설정
if [ "$ENVIRONMENT" = "prod" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
    PROJECT_NAME="smartcast-aiagent-prod"
else
    echo "❌ 지원하지 않는 환경입니다: ${ENVIRONMENT}"
    echo "지원 환경: prod"
    exit 1
fi

# 1. 환경변수 파일 확인
ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
    echo "⚠️  환경변수 파일이 없습니다. 생성합니다..."
    cat > .env << EOF
# SmartCast AI Agent 환경변수
OPENAI_API_KEY=your_openai_api_key_here
BROKER_HOST=external-broker.yourdomain.com
BROKER_PORT=5555
LOG_LEVEL=INFO

# PostgreSQL 설정
POSTGRES_DB=aiagent
POSTGRES_USER=aiagent
POSTGRES_PASSWORD=aiagent123
POSTGRES_PORT=5432
EOF
    echo "📝 .env 파일을 생성했습니다. 설정을 확인하고 다시 실행해주세요."
    exit 1
fi

# 2. 필수 환경변수 확인
source .env
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
    echo "❌ OPENAI_API_KEY가 설정되지 않았습니다!"
    exit 1
fi

if [ -z "$BROKER_HOST" ] || [ "$BROKER_HOST" = "external-broker.yourdomain.com" ]; then
    echo "❌ BROKER_HOST가 설정되지 않았습니다!"
    exit 1
fi

# 3. Docker Compose 파일 생성 (이미지 버전 포함)
echo "📄 Docker Compose 파일 업데이트 중..."
cat > ${COMPOSE_FILE} << EOF
# 운영용 Docker Compose (외부 브로커 전용)
# 배포 버전: ${VERSION}
# 생성 시간: $(date '+%Y-%m-%d %H:%M:%S')

services:
  ai-agent:
    image: ${REGISTRY}/${IMAGE_NAME}:${VERSION}
    container_name: smartcast-aiagent-ai-agent-prod
    environment:
      - OPENAI_API_KEY=\${OPENAI_API_KEY}
      - BROKER_HOST=\${BROKER_HOST}
      - BROKER_PORT=\${BROKER_PORT}
      - LOG_LEVEL=\${LOG_LEVEL:-INFO}
      - DATABASE_URL=postgresql://aiagent:aiagent123@postgres:5432/aiagent
      - TZ=Asia/Seoul
    volumes:
      - ./logs:/app/logs
      - /etc/localtime:/etc/localtime:ro
    restart: unless-stopped
    depends_on:
      - postgres
    networks:
      - aiagent-prod-network
    deploy:
      resources:
        limits:
          cpus: '30.0'
          memory: 56G
        reservations:
          cpus: '8.0'
          memory: 8G

  postgres:
    image: postgres:15-alpine
    container_name: smartcast-aiagent-postgres-prod
    ports:
      - "\${POSTGRES_PORT:-5432}:5432"
    environment:
      - POSTGRES_DB=\${POSTGRES_DB:-aiagent}
      - POSTGRES_USER=\${POSTGRES_USER:-aiagent}
      - POSTGRES_PASSWORD=\${POSTGRES_PASSWORD:-aiagent123}
      - TZ=Asia/Seoul
    volumes:
      - postgres_prod_data:/var/lib/postgresql/data
      - /etc/localtime:/etc/localtime:ro
    restart: unless-stopped
    networks:
      - aiagent-prod-network
    deploy:
      resources:
        limits:
          cpus: '8.0'
          memory: 16G
        reservations:
          cpus: '2.0'
          memory: 4G

networks:
  aiagent-prod-network:
    driver: bridge

volumes:
  postgres_prod_data:
  logs:
EOF

# 4. 기존 서비스 중지
echo "🛑 기존 서비스 중지 중..."
docker compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} down

# 5. 최신 이미지 Pull
echo "📥 최신 이미지 다운로드 중..."
docker pull ${REGISTRY}/${IMAGE_NAME}:${VERSION}

# 6. 서비스 시작
echo "🚀 서비스 시작 중..."
docker compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} up -d

# 7. 배포 결과 확인
sleep 10
echo ""
echo "📊 배포 상태 확인..."
docker compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} ps

# 8. 로그 확인
echo ""
echo "📋 최근 로그 (마지막 20줄):"
docker compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} logs --tail=20 ai-agent

echo ""
echo "✅ 배포 완료!"
echo ""
echo "🔧 유용한 명령어:"
echo "- 상태 확인: docker compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} ps"
echo "- 로그 확인: docker compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} logs -f ai-agent"
echo "- 서비스 중지: docker compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} down"
echo "- 재시작: docker compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} restart" 