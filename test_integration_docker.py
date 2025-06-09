#!/usr/bin/env python3
"""
Phase 6: 통합 테스트 및 검증 스크립트 (Docker 내부용)
Docker 컨테이너 내부에서 실행하는 버전
"""

import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, Any

# 테스트 설정 (Docker 내부용)
BASE_URL = "http://localhost:8000"  # 컨테이너 내부에서는 8000 포트
TEST_RESULTS = []

def log_test(test_name: str, success: bool, message: str = "", response_time: float = 0):
    """테스트 결과 로깅"""
    result = {
        "test_name": test_name,
        "success": success,
        "message": message,
        "response_time": response_time,
        "timestamp": datetime.now().isoformat()
    }
    TEST_RESULTS.append(result)
    
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} | {test_name} | {response_time:.3f}s | {message}")

def test_health_check():
    """헬스체크 엔드포인트 테스트"""
    start_time = time.time()
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy" and data.get("database") == "connected":
                log_test("Health Check", True, "서버 정상 작동", response_time)
                return True
            else:
                log_test("Health Check", False, f"상태 이상: {data}", response_time)
                return False
        else:
            log_test("Health Check", False, f"HTTP {response.status_code}", response_time)
            return False
    except Exception as e:
        response_time = time.time() - start_time
        log_test("Health Check", False, f"연결 실패: {str(e)}", response_time)
        return False

def test_swagger_docs():
    """Swagger 문서 접근 테스트"""
    start_time = time.time()
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            log_test("Swagger Docs", True, "문서 접근 가능", response_time)
            return True
        else:
            log_test("Swagger Docs", False, f"HTTP {response.status_code}", response_time)
            return False
    except Exception as e:
        response_time = time.time() - start_time
        log_test("Swagger Docs", False, f"접근 실패: {str(e)}", response_time)
        return False

def test_parsing_errors_list():
    """파싱 에러 목록 조회 테스트"""
    start_time = time.time()
    try:
        response = requests.get(f"{BASE_URL}/api/v1/admin/parsing-errors", timeout=10)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            if "data" in data and "total" in data:
                log_test("Parsing Errors List", True, f"총 {data['total']}개 에러", response_time)
                return True, data
            else:
                log_test("Parsing Errors List", False, "응답 구조 이상", response_time)
                return False, None
        else:
            log_test("Parsing Errors List", False, f"HTTP {response.status_code}: {response.text}", response_time)
            return False, None
    except Exception as e:
        response_time = time.time() - start_time
        log_test("Parsing Errors List", False, f"요청 실패: {str(e)}", response_time)
        return False, None

def test_statistics_endpoint():
    """통계 엔드포인트 테스트"""
    start_time = time.time()
    try:
        response = requests.get(f"{BASE_URL}/api/v1/admin/parsing-errors/statistics/overview", timeout=10)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            required_fields = ["ERROR", "FIXED", "TESTING", "COMPLETED", "TOTAL"]
            
            if all(field in data for field in required_fields):
                total = sum(data[field] for field in required_fields[:-1])
                log_test("Statistics API", True, f"총계: {data['TOTAL']}, 계산값: {total}", response_time)
                return True
            else:
                log_test("Statistics API", False, "필수 필드 누락", response_time)
                return False
        else:
            log_test("Statistics API", False, f"HTTP {response.status_code}", response_time)
            return False
    except Exception as e:
        response_time = time.time() - start_time
        log_test("Statistics API", False, f"통계 실패: {str(e)}", response_time)
        return False

def run_integration_tests():
    """모든 통합 테스트 실행"""
    print("🚀 Phase 6: 통합 테스트 시작 (Docker 내부)")
    print("=" * 80)
    
    # 기본 연결 테스트
    print("\n📋 1. 기본 연결 테스트")
    test_health_check()
    test_swagger_docs()
    
    # API 엔드포인트 테스트
    print("\n📋 2. API 엔드포인트 테스트")
    test_parsing_errors_list()
    test_statistics_endpoint()
    
    # 결과 요약
    print("\n" + "=" * 80)
    print("📊 테스트 결과 요약")
    print("=" * 80)
    
    total_tests = len(TEST_RESULTS)
    passed_tests = sum(1 for result in TEST_RESULTS if result["success"])
    failed_tests = total_tests - passed_tests
    
    print(f"총 테스트: {total_tests}")
    print(f"성공: {passed_tests} ✅")
    print(f"실패: {failed_tests} ❌")
    print(f"성공률: {(passed_tests/total_tests)*100:.1f}%")
    
    # 평균 응답 시간
    if total_tests > 0:
        avg_response_time = sum(result["response_time"] for result in TEST_RESULTS) / total_tests
        print(f"평균 응답 시간: {avg_response_time:.3f}초")
    
    # 실패한 테스트 상세
    if failed_tests > 0:
        print("\n❌ 실패한 테스트:")
        for result in TEST_RESULTS:
            if not result["success"]:
                print(f"  - {result['test_name']}: {result['message']}")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1) 