#!/bin/bash

# SmartCast AI Agent 이미지 푸시 스크립트
# 사용법: ./push.sh [VERSION]

VERSION=${1:-latest}
IMAGE_NAME="smartcast-aiagent"
REGISTRY="younggyun"  # Docker Hub 사용시: your-dockerhub-username

echo "🚀 SmartCast AI Agent 이미지 푸시 시작..."

# Registry 설정 확인
if [ "$REGISTRY" = "your-registry.com" ]; then
    echo "❌ Registry 설정이 필요합니다!"
    echo "📝 build.sh와 push.sh에서 REGISTRY 변수를 설정해주세요."
    echo ""
    echo "예시:"
    echo "- Docker Hub: REGISTRY=\"your-dockerhub-username\""
    echo "- Private Registry: REGISTRY=\"registry.company.com\""
    exit 1
fi

# 1. Registry 로그인 확인
echo "🔐 Registry 로그인 상태 확인..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker가 실행되지 않았습니다!"
    exit 1
fi

# 2. 이미지 존재 확인
if ! docker images | grep -q "${REGISTRY}/${IMAGE_NAME}"; then
    echo "❌ 이미지가 존재하지 않습니다!"
    echo "먼저 ./build.sh ${VERSION}을 실행해주세요."
    exit 1
fi

# 3. 이미지 푸시
echo "📤 이미지 푸시 중..."
echo "🎯 대상: ${REGISTRY}/${IMAGE_NAME}:${VERSION}"

docker push ${REGISTRY}/${IMAGE_NAME}:${VERSION}
docker push ${REGISTRY}/${IMAGE_NAME}:latest

if [ $? -eq 0 ]; then
    echo "✅ 이미지 푸시 완료!"
    echo ""
    echo "🌐 푸시된 이미지:"
    echo "- ${REGISTRY}/${IMAGE_NAME}:${VERSION}"
    echo "- ${REGISTRY}/${IMAGE_NAME}:latest"
    echo ""
    echo "🚀 다음 단계:"
    echo "서버에서 다음 명령어로 배포하세요:"
    echo "curl -fsSL https://your-repo/deploy.sh | bash -s ${VERSION}"
else
    echo "❌ 이미지 푸시 실패!"
    exit 1
fi 