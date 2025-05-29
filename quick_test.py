#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostgreSQL 통합 완료 확인 - 빠른 테스트
"""
import os
import sys

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 환경 변수 설정
os.environ['DATABASE_URL'] = 'postgresql://aiagent:password@localhost:5432/aiagent_db'

def test_imports():
    """기본 import 테스트"""
    print("🔧 Import 테스트 시작...")
    
    try:
        # 데이터베이스 관련
        from aiagent.database import check_db_connection, create_tables
        print("✅ PostgreSQL database import 성공")
        
        # 기존 모델 (aiagent 패키지)
        from aiagent.models.receipt_record import ReceiptRecord
        print("✅ ReceiptRecord 모델 import 성공")
        
        # 새로운 모델들 (aiagent 패키지)
        from aiagent.models.parsing_error import ParsingError
        from aiagent.models.parsing_rule import ParsingRule  
        from aiagent.models.ml_training_data import MLTrainingData
        print("✅ 새로운 모델들 import 성공")
        
        # 파서
        from aiagent.services.parser import parser
        print("✅ Parser import 성공")
        
        # 프로세서
        from aiagent.services.processor import BillProcessor
        print("✅ BillProcessor import 성공")
        
        return True
        
    except Exception as e:
        print(f"❌ Import 실패: {e}")
        return False

def test_db_connection():
    """데이터베이스 연결 테스트"""
    print("\n🔗 PostgreSQL 연결 테스트...")
    
    try:
        from aiagent.database import check_db_connection
        
        if check_db_connection():
            print("✅ PostgreSQL 연결 성공!")
            return True
        else:
            print("❌ PostgreSQL 연결 실패")
            return False
            
    except Exception as e:
        print(f"❌ 연결 테스트 실패: {e}")
        return False

def test_parser_features():
    """새로운 파서 기능 확인"""
    print("\n🧩 새로운 파서 기능 확인...")
    
    try:
        from aiagent.services.parser import parser
        
        if not parser:
            print("❌ 파서 초기화 실패")
            return False
            
        # 새로운 메서드 확인
        new_methods = [
            'wrap_generated_type',
            '_extract_type', 
            '_validate_type_structure',
            'merge_rule'
        ]
        
        for method in new_methods:
            if hasattr(parser, method):
                print(f"   ✅ {method}")
            else:
                print(f"   ❌ {method} 누락")
                return False
                
        print("✅ 모든 새로운 파서 기능 확인 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 파서 기능 테스트 실패: {e}")
        return False

def test_directory_cleanup():
    """디렉토리 정리 확인"""
    print("\n🧹 디렉토리 정리 상태 확인...")
    
    # aiagent/db 디렉토리가 삭제되었는지 확인
    if os.path.exists('aiagent/db'):
        print("❌ aiagent/db 디렉토리가 아직 남아있음")
        return False
    else:
        print("✅ aiagent/db 디렉토리 삭제 완료")
    
    # aiagent.db 파일이 삭제되었는지 확인
    if os.path.exists('aiagent.db'):
        print("❌ aiagent.db 파일이 아직 남아있음")
        return False
    else:
        print("✅ aiagent.db 파일 삭제 완료")
        
    print("✅ SQLite 관련 파일/디렉토리 정리 완료!")
    return True

def main():
    """메인 테스트"""
    print("🚀 PostgreSQL 통합 완료 검증 시작!")
    print("=" * 50)
    
    tests = [
        ("Import 테스트", test_imports),
        ("디렉토리 정리", test_directory_cleanup),
        ("데이터베이스 연결", test_db_connection),
        ("새로운 파서 기능", test_parser_features),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} 예외: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 결과: {passed}개 통과, {failed}개 실패")
    
    if failed == 0:
        print("🎉 PostgreSQL 통합 완료!")
        print("💡 다음 단계: FastAPI 서버 실행 및 관리자 API 테스트")
    else:
        print(f"⚠️  {failed}개 문제 발견. 수정이 필요합니다.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    print(f"\n종료 코드: {0 if success else 1}") 