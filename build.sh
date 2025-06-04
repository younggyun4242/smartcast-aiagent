#!/bin/bash

# SmartCast AI Agent 이미지 빌드 스크립트
# 사용법: ./build.sh [VERSION]

VERSION=${1:-latest}
IMAGE_NAME="smartcast-aiagent"
REGISTRY="younggyun"  # Docker Hub 사용시: your-dockerhub-username

echo "🔨 SmartCast AI Agent 이미지 빌드 시작..."
echo "📦 이미지명: ${IMAGE_NAME}:${VERSION}"

# 1. 이미지 빌드
echo "⚙️  이미지 빌드 중..."
docker build -t ${IMAGE_NAME}:${VERSION} .

if [ $? -eq 0 ]; then
    echo "✅ 이미지 빌드 완료!"
    
    # 2. 태그 추가 (Registry용)
    if [ "$REGISTRY" != "your-registry.com" ]; then
        echo "🏷️  Registry 태그 추가 중..."
        docker tag ${IMAGE_NAME}:${VERSION} ${REGISTRY}/${IMAGE_NAME}:${VERSION}
        docker tag ${IMAGE_NAME}:${VERSION} ${REGISTRY}/${IMAGE_NAME}:latest
        echo "✅ 태그 추가 완료!"
    fi
    
    # 3. 빌드된 이미지만 정확히 표시
    echo "📋 생성된 이미지:"
    echo "🎯 메인 이미지:"
    docker images | grep "^${IMAGE_NAME} " | grep "${VERSION}"
    
    if [ "$REGISTRY" != "your-registry.com" ]; then
        echo "🏷️  Registry 태그:"
        docker images | grep "^${REGISTRY}/${IMAGE_NAME} "
    fi
    
    # 4. 불필요한 이미지 정리 안내
    echo ""
    echo "🧹 이전 개발환경 이미지 정리 (선택사항):"
    echo "docker image prune -f"
    echo "docker rmi smartcast-aiagent-broker:latest smartcast-aiagent-ai-agent:latest 2>/dev/null || true"
    
    echo ""
    echo "🚀 다음 단계:"
    echo "1. 이미지 푸시: ./push.sh ${VERSION}"
    echo "2. 서버 배포: ./deploy.sh ${VERSION}"
    
else
    echo "❌ 이미지 빌드 실패!"
    exit 1
fi 