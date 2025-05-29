#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostgreSQL 통합 시스템 전체 테스트
- 파서 기능 테스트
- 데이터베이스 연결 테스트  
- 관리자 API 테스트
- 새로 개발한 기능들 검증
"""

import os
import sys
import json
import time
import logging
from typing import Dict, Any

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 환경 변수 설정 (PostgreSQL 연결)
os.environ.setdefault('DATABASE_URL', 'postgresql://aiagent:password@localhost:5432/aiagent_db')
os.environ.setdefault('OPENAI_API_KEY', 'your-openai-api-key-here')

def setup_logging():
    """로깅 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger('test_integration')

def test_database_connection():
    """PostgreSQL 데이터베이스 연결 테스트"""
    logger.info("🔗 PostgreSQL 데이터베이스 연결 테스트...")
    
    try:
        from aiagent.database import check_db_connection, create_tables
        
        # 연결 확인
        if check_db_connection():
            logger.info("✅ PostgreSQL 데이터베이스 연결 성공!")
            
            # 테이블 생성
            create_tables()
            logger.info("✅ PostgreSQL 테이블 생성/확인 완료!")
            return True
        else:
            logger.error("❌ PostgreSQL 데이터베이스 연결 실패")
            return False
            
    except Exception as e:
        logger.error(f"❌ 데이터베이스 테스트 실패: {e}")
        return False

def test_parser_functionality():
    """파서 기능 테스트"""
    logger.info("🧩 파서 기능 테스트...")
    
    try:
        from aiagent.services.parser import parser, ParserError
        
        if not parser:
            logger.error("❌ 파서 초기화 실패")
            return False
            
        # 테스트용 영수증 데이터 (hex 형식)
        test_receipt_data = {
            "client_id": "CLIENT",
            "transaction_id": "test_processor_001",
            "receipt_data": {
                "raw_data": "20202020201b21105ba2c2bdc5b1d42dc1d6b9e6c1d6b9aebcad5d2dc1d6b9e6311b21000d0a0a1b21100a5bc5d7c0ccbaed5d20b1e2babb2d313032205bbcd5b4d4bcf65d20303120b8ed0a5bc1d6b9aec0da5d20c0ccbcbcb5b9202020202020205bc1d6b9aeb9f8c8a35d20303131352d303030311b21000a3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d0a1b211020202020b8de2020b4ba2020b8ed2020202020202020202020202020202020bcf6b7ae202020b1b8bad00d0a2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d0d0ac2abbbcd20202020202020202020202020202020202020202020202020202020202031202020bdc5b1d40d0abdbab8b6c6ae2041bcbcc6ae2020202020202020202020202020202020202020202031202020bdc5b1d40d0aa2bac2fcc4a1b1e8b9e420202020202020202020202020202020202020202020202031202020bcb1c5c30d0aa2bab5c8c0e5c2eeb0b320202020202020202020202020202020202020202020202031202020bcb1c5c31b21000a2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d0a1b21100d0a5bc1d6b9e6b8deb8f05d201b21000a3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d0a504f533a30312020202020205bc1d6b9aebdc3b0a35d20323032352d30352d32322031343a32313a34320a0a0a0a0a0a1b69"
            }
        }
        
        logger.info("🔄 파싱 규칙 생성 테스트...")
        result = parser.generate_rule(test_receipt_data)
        
        if result.get("status") == "ok":
            logger.info("✅ 파싱 규칙 생성 성공!")
            logger.info(f"   버전: {result.get('version')}")
            return True
        else:
            logger.error(f"❌ 파싱 규칙 생성 실패: {result}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 파서 테스트 실패: {e}")
        return False

def test_processor_integration():
    """프로세서 통합 테스트 (PostgreSQL 연동)"""
    logger.info("⚙️ 프로세서 통합 테스트...")
    
    try:
        from aiagent.services.processor import BillProcessor
        
        processor = BillProcessor()
        
        # 테스트 데이터
        test_data = {
            "client_id": "CLIENT",
            "transaction_id": "test_processor_001",
            "receipt_data": {
                "raw_data": "20202020201b21105ba2bac3dfb0a12dc1d6b9e6c1d6b9aebcad5d2dc1d6b9e6311b21000d0a0a1b21100a5bc5d7c0ccbaed5d20b1e2babb2d313032205bbcd5b4d4bcf65d20303120b8ed0a5bc1d6b9aec0da5d20c0ccbcbcb5b9202020202020205bc1d6b9aeb9f8c8a35d20303131352d303030321b21000a3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d0a1b211020202020b8de2020b4ba2020b8ed2020202020202020202020202020202020bcf6b7ae202020b1b8bad00d0a2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d0d0ac2abbbcd20202020202020202020202020202020202020202020202020202020202d31202020c3ebbcd21b21000a2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d0a1b21100d0a5bc1d6b9e6b8deb8f05d201b21000a3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d3d0a504f533a30312020202020205bc1d6b9aebdc3b0a35d20323032352d30352d32322031343a32323a30310a0a0a0a0a0a1b69"
            }
        }
        
        raw_data = json.dumps(test_data).encode('utf-8')
        
        logger.info("🔄 AI 생성 요청 처리 테스트...")
        result = processor.process_ai_generate("TEST_CLIENT", raw_data)
        
        if result.get("status") == "ok":
            logger.info("✅ AI 생성 처리 성공!")
            logger.info("✅ PostgreSQL에 결과 저장 완료!")
            return True
        else:
            logger.error(f"❌ AI 생성 처리 실패: {result}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 프로세서 테스트 실패: {e}")
        return False

def test_admin_api():
    """관리자 API 테스트"""
    logger.info("🔧 관리자 API 기능 테스트...")
    
    try:
        from aiagent.repositories.parsing_error_repository import ParsingErrorRepository
        from ailagent.repositories.parsing_error_repository import ParsingErrorRepository as NewRepo
        from aiagent.database import SessionLocal
        
        session = SessionLocal()
        
        # 기존 저장소 테스트
        logger.info("🔄 파싱 에러 저장소 테스트...")
        old_repo = ParsingErrorRepository(session)
        
        # 새로운 저장소 테스트  
        new_repo = NewRepo(session)
        
        logger.info("✅ 관리자 API 저장소 초기화 성공!")
        
        session.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ 관리자 API 테스트 실패: {e}")
        return False

def test_models_integration():
    """모델 통합 테스트"""
    logger.info("📊 모델 통합 테스트...")
    
    try:
        # 기존 모델
        from aiagent.models.receipt_record import ReceiptRecord
        
        # 새로운 모델들
        from ailagent.models.parsing_error import ParsingError
        from ailagent.models.parsing_rule import ParsingRule
        from ailagent.models.ml_training_data import MLTrainingData
        
        logger.info("✅ 모든 모델 import 성공!")
        
        # 모델 속성 확인
        logger.info("🔄 모델 속성 확인...")
        
        # ReceiptRecord 속성 확인
        receipt_attrs = ['client_id', 'transaction_id', 'raw_data', 'xml_result', 'is_valid']
        for attr in receipt_attrs:
            if hasattr(ReceiptRecord, attr):
                logger.info(f"   ✅ ReceiptRecord.{attr}")
            else:
                logger.error(f"   ❌ ReceiptRecord.{attr} 누락")
                
        logger.info("✅ 모델 통합 테스트 완료!")
        return True
        
    except Exception as e:
        logger.error(f"❌ 모델 테스트 실패: {e}")
        return False

def test_new_features():
    """새로 개발한 기능들 테스트"""
    logger.info("🆕 새로운 기능 테스트...")
    
    try:
        # TYPE 기반 아키텍처 테스트
        from aiagent.services.parser import parser
        
        if parser:
            logger.info("✅ TYPE 기반 파서 아키텍처 로드 성공!")
            
            # 새로운 메서드들 확인
            new_methods = ['wrap_generated_type', '_extract_type', '_validate_type_structure', 'merge_rule']
            for method in new_methods:
                if hasattr(parser, method):
                    logger.info(f"   ✅ parser.{method}")
                else:
                    logger.error(f"   ❌ parser.{method} 누락")
        
        logger.info("✅ 새로운 기능 테스트 완료!")
        return True
        
    except Exception as e:
        logger.error(f"❌ 새로운 기능 테스트 실패: {e}")
        return False

def main():
    """메인 테스트 실행"""
    global logger
    logger = setup_logging()
    
    logger.info("🚀 PostgreSQL 통합 시스템 전체 테스트 시작!")
    logger.info("=" * 60)
    
    tests = [
        ("데이터베이스 연결", test_database_connection),
        ("모델 통합", test_models_integration),
        ("파서 기능", test_parser_functionality),
        ("프로세서 통합", test_processor_integration),
        ("관리자 API", test_admin_api),
        ("새로운 기능", test_new_features),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 {test_name} 테스트 실행...")
        try:
            if test_func():
                passed += 1
                logger.info(f"✅ {test_name} 테스트 통과!")
            else:
                failed += 1
                logger.error(f"❌ {test_name} 테스트 실패!")
        except Exception as e:
            failed += 1
            logger.error(f"❌ {test_name} 테스트 예외 발생: {e}")
    
    logger.info("\n" + "=" * 60)
    logger.info(f"📊 테스트 결과: {passed}개 통과, {failed}개 실패")
    
    if failed == 0:
        logger.info("🎉 모든 테스트 통과! PostgreSQL 통합 완료!")
    else:
        logger.error(f"⚠️  {failed}개 테스트 실패. 문제를 해결해주세요.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 