#!/bin/bash

# 빌드/실행 스크립트
case "$1" in
  "prod")
    echo "🚀 실무용 환경 실행 (.dockerignore 적용)"
    docker-compose down
    docker-compose up --build -d
    echo "📦 빌드된 이미지 크기 확인:"
    docker images smartcast-aiagent-ai-agent
    ;;
  "test")
    echo "🧪 테스트용 환경 실행"
    docker-compose -f docker-compose.test.yml down
    docker-compose -f docker-compose.test.yml up --build -d
    ;;
  "dev")
    echo "🛠️ 개발용 환경 실행"
    docker-compose -f docker-compose.dev.yml down
    docker-compose -f docker-compose.dev.yml up --build -d
    ;;
  "check")
    echo "🔍 실무용 이미지 내용 확인"
    docker run --rm -it smartcast-aiagent-ai-agent ls -la /app
    ;;
  *)
    echo "사용법: $0 {prod|test|dev|check}"
    echo "  prod: 실무용 환경"
    echo "  test: 테스트용 환경" 
    echo "  dev: 개발용 환경"
    echo "  check: 실무용 이미지 내용 확인"
    exit 1
    ;;
esac 