#!/bin/bash

# 테스트 실행 스크립트
echo "🧪 테스트 환경에서 파서 테스트 실행"

# 테스트 환경 실행
docker-compose -f docker-compose.test.yml up -d

# 잠시 대기 (서비스 시작 시간)
sleep 5

# 테스트 실행
python test_parser.py

# 결과 확인
echo "📋 테스트 완료" 