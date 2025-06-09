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

# 1. Git에서 최신 코드 받기
echo "📥 최신 설정 파일 받기..."
if [ -d ".git" ]; then
    git pull origin master
    echo "✅ Git pull 완료"
else
    echo "⚠️  Git 저장소가 아닙니다. 수동으로 최신 파일을 확인하세요."
fi

# 2. Docker Compose 파일 존재 확인
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "❌ ${COMPOSE_FILE} 파일이 없습니다!"
    echo "Git에서 최신 파일을 받아오거나, 파일을 생성하세요."
    exit 1
fi

# 3. 환경변수 파일 확인
ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
    echo "⚠️  환경변수 파일이 없습니다. 생성합니다..."
    cat > .env << EOF
# SmartCast AI Agent 환경변수
OPENAI_API_KEY=your_openai_api_key_here
BROKER_HOST=external-broker.yourdomain.com
BROKER_PORT=5555
LOG_LEVEL=INFO

# API 서버 포트
API_PORT=8000

# PostgreSQL 설정
POSTGRES_DB=aiagent
POSTGRES_USER=aiagent
POSTGRES_PASSWORD=aiagent123
POSTGRES_PORT=5432
EOF
    echo "📝 .env 파일을 생성했습니다. 설정을 확인하고 다시 실행해주세요."
    exit 1
fi

# 4. 필수 환경변수 확인
source .env
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
    echo "❌ OPENAI_API_KEY가 설정되지 않았습니다!"
    exit 1
fi

if [ -z "$BROKER_HOST" ] || [ "$BROKER_HOST" = "external-broker.yourdomain.com" ]; then
    echo "❌ BROKER_HOST가 설정되지 않았습니다!"
    exit 1
fi

# 5. 현재 사용할 Docker Compose 파일 표시
echo "📄 사용할 Docker Compose 파일: ${COMPOSE_FILE}"
echo "🏷️  배포할 이미지 버전: ${REGISTRY}/${IMAGE_NAME}:${VERSION}"

# 6. docker-compose.yml에서 이미지 태그 업데이트 (선택적)
if [ "$VERSION" != "latest" ]; then
    echo "🏷️  이미지 태그를 ${VERSION}으로 업데이트 중..."
    sed -i.bak "s|${REGISTRY}/${IMAGE_NAME}:.*|${REGISTRY}/${IMAGE_NAME}:${VERSION}|g" ${COMPOSE_FILE}
    echo "✅ 이미지 태그 업데이트 완료"
fi

# 7. 기존 서비스 중지
echo "🛑 기존 서비스 중지 중..."
docker compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} down

# 8. 최신 이미지 Pull
echo "📥 최신 이미지 다운로드 중..."
docker pull ${REGISTRY}/${IMAGE_NAME}:${VERSION}

# 9. 서비스 시작
echo "🚀 서비스 시작 중..."
docker compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} up -d

# 10. 배포 결과 확인
sleep 10
echo ""
echo "📊 배포 상태 확인..."
docker compose -f ${COMPOSE_FILE} -p ${PROJECT_NAME} ps

# 11. 로그 확인
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