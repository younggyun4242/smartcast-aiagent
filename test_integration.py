#!/usr/bin/env python3
"""
Phase 6: 통합 테스트 및 검증 스크립트
로컬 Docker 환경에서 API 엔드포인트를 테스트합니다.
"""

import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, Any

# 테스트 설정
BASE_URL = "http://localhost:8001"
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

def test_parsing_errors_pagination():
    """파싱 에러 페이징 테스트"""
    start_time = time.time()
    try:
        # 첫 번째 페이지
        response1 = requests.get(f"{BASE_URL}/api/v1/admin/parsing-errors?page=1&limit=5", timeout=10)
        # 두 번째 페이지
        response2 = requests.get(f"{BASE_URL}/api/v1/admin/parsing-errors?page=2&limit=5", timeout=10)
        
        response_time = time.time() - start_time
        
        if response1.status_code == 200 and response2.status_code == 200:
            data1 = response1.json()
            data2 = response2.json()
            
            if data1.get("page") == 1 and data2.get("page") == 2:
                log_test("Pagination Test", True, f"페이징 정상 작동", response_time)
                return True
            else:
                log_test("Pagination Test", False, "페이지 번호 불일치", response_time)
                return False
        else:
            log_test("Pagination Test", False, f"HTTP 에러", response_time)
            return False
    except Exception as e:
        response_time = time.time() - start_time
        log_test("Pagination Test", False, f"페이징 실패: {str(e)}", response_time)
        return False

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

def test_recent_errors_endpoint():
    """최근 에러 엔드포인트 테스트"""
    start_time = time.time()
    try:
        response = requests.get(f"{BASE_URL}/api/v1/admin/parsing-errors/recent?hours=24", timeout=10)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            if "data" in data and "hours" in data and "count" in data:
                log_test("Recent Errors API", True, f"24시간 내 {data['count']}개 에러", response_time)
                return True
            else:
                log_test("Recent Errors API", False, "응답 구조 이상", response_time)
                return False
        else:
            log_test("Recent Errors API", False, f"HTTP {response.status_code}", response_time)
            return False
    except Exception as e:
        response_time = time.time() - start_time
        log_test("Recent Errors API", False, f"최근 에러 실패: {str(e)}", response_time)
        return False

def test_invalid_endpoints():
    """잘못된 엔드포인트 테스트 (404 처리)"""
    start_time = time.time()
    try:
        response = requests.get(f"{BASE_URL}/api/v1/admin/non-existent-endpoint", timeout=5)
        response_time = time.time() - start_time
        
        if response.status_code == 404:
            log_test("404 Error Handling", True, "404 정상 처리", response_time)
            return True
        else:
            log_test("404 Error Handling", False, f"예상과 다른 응답: {response.status_code}", response_time)
            return False
    except Exception as e:
        response_time = time.time() - start_time
        log_test("404 Error Handling", False, f"테스트 실패: {str(e)}", response_time)
        return False

def test_database_connection():
    """데이터베이스 연결 지속성 테스트"""
    start_time = time.time()
    success_count = 0
    
    for i in range(5):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=3)
            if response.status_code == 200:
                data = response.json()
                if data.get("database") == "connected":
                    success_count += 1
            time.sleep(0.5)  # 0.5초 간격
        except:
            pass
    
    response_time = time.time() - start_time
    
    if success_count == 5:
        log_test("DB Connection Stability", True, f"5회 연속 연결 성공", response_time)
        return True
    else:
        log_test("DB Connection Stability", False, f"5회 중 {success_count}회 성공", response_time)
        return False

def run_integration_tests():
    """모든 통합 테스트 실행"""
    print("🚀 Phase 6: 통합 테스트 시작")
    print("=" * 80)
    
    # 기본 연결 테스트
    print("\n📋 1. 기본 연결 테스트")
    test_health_check()
    test_swagger_docs()
    test_database_connection()
    
    # API 엔드포인트 테스트
    print("\n📋 2. API 엔드포인트 테스트")
    test_parsing_errors_list()
    test_parsing_errors_pagination()
    test_statistics_endpoint()
    test_recent_errors_endpoint()
    
    # 에러 처리 테스트
    print("\n📋 3. 에러 처리 테스트")
    test_invalid_endpoints()
    
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
    avg_response_time = sum(result["response_time"] for result in TEST_RESULTS) / total_tests
    print(f"평균 응답 시간: {avg_response_time:.3f}초")
    
    # 실패한 테스트 상세
    if failed_tests > 0:
        print("\n❌ 실패한 테스트:")
        for result in TEST_RESULTS:
            if not result["success"]:
                print(f"  - {result['test_name']}: {result['message']}")
    
    # JSON 결과 저장
    with open("integration_test_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "total": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": (passed_tests/total_tests)*100,
                "avg_response_time": avg_response_time,
                "timestamp": datetime.now().isoformat()
            },
            "details": TEST_RESULTS
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 상세 결과: integration_test_results.json")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1) 