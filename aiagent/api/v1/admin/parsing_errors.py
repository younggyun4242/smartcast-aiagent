"""
파싱 에러 관리 API 엔드포인트
관리자가 파싱 에러를 조회, 수정, 테스트, 전송할 수 있는 API
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from aiagent.api.dependencies import get_admin_service
from aiagent.api.v1.admin.schemas import (
    ParsingErrorListResponse,
    ParsingErrorDetailResponse,
    UpdateParsingRuleRequest,
    UpdateParsingRuleResponse,
    TestParsingRuleRequest,
    TestParsingRuleResponse,
    SubmitParsingRuleRequest,
    SubmitParsingRuleResponse,
    ErrorStatisticsResponse,
    RecentErrorsResponse,
    BulkUpdateStatusRequest,
    BulkUpdateStatusResponse,
    ErrorResponse
)
from aiagent.services.admin_service import AdminService
from aiagent.exceptions import NotFoundError, ValidationError, BusinessLogicError, ParseRuleTestError
from aiagent.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/parsing-errors", tags=["파싱 에러 관리"])

@router.get("", response_model=ParsingErrorListResponse)
async def get_parsing_errors(
    client_id: Optional[str] = Query(None, description="클라이언트 ID 필터"),
    status: Optional[str] = Query(None, description="상태 필터 (ERROR, FIXED, TESTING, COMPLETED)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(20, ge=1, le=100, description="페이지당 항목 수"),
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    파싱 에러 목록 조회
    
    - **client_id**: 특정 클라이언트의 에러만 조회 (선택사항)
    - **status**: 특정 상태의 에러만 조회 (선택사항)
    - **page**: 페이지 번호 (기본값: 1)
    - **limit**: 페이지당 항목 수 (기본값: 20, 최대: 100)
    """
    try:
        result = admin_service.get_parsing_errors(
            client_id=client_id,
            status=status,
            page=page,
            limit=limit
        )
        
        logger.info(f"파싱 에러 목록 조회 API 호출: client_id={client_id}, status={status}, page={page}")
        return result
        
    except ValidationError as e:
        logger.warning(f"파싱 에러 목록 조회 검증 실패: {e.message}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except BusinessLogicError as e:
        logger.error(f"파싱 에러 목록 조회 비즈니스 로직 오류: {e.message}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message)

@router.get("/{error_id}", response_model=ParsingErrorDetailResponse)
async def get_parsing_error_detail(
    error_id: int,
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    특정 파싱 에러 상세 조회
    
    - **error_id**: 조회할 에러의 ID
    """
    try:
        result = admin_service.get_parsing_error_detail(error_id)
        
        logger.info(f"파싱 에러 상세 조회 API 호출: error_id={error_id}")
        return result
        
    except NotFoundError as e:
        logger.warning(f"파싱 에러 상세 조회 실패: {e.message}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except BusinessLogicError as e:
        logger.error(f"파싱 에러 상세 조회 비즈니스 로직 오류: {e.message}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message)

@router.put("/{error_id}/rule", response_model=UpdateParsingRuleResponse)
async def update_parsing_rule(
    error_id: int,
    request: UpdateParsingRuleRequest,
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    파싱룰 수정
    
    - **error_id**: 수정할 에러의 ID
    - **xml_content**: 새로운 파싱룰 XML 내용
    """
    try:
        result = admin_service.update_parsing_rule(error_id, request.xml_content)
        
        logger.info(f"파싱룰 수정 API 호출: error_id={error_id}")
        return UpdateParsingRuleResponse(**result)
        
    except NotFoundError as e:
        logger.warning(f"파싱룰 수정 실패: {e.message}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ValidationError as e:
        logger.warning(f"파싱룰 수정 검증 실패: {e.message}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except BusinessLogicError as e:
        logger.error(f"파싱룰 수정 비즈니스 로직 오류: {e.message}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message)

@router.post("/{error_id}/test", response_model=TestParsingRuleResponse)
async def test_parsing_rule(
    error_id: int,
    request: TestParsingRuleRequest,
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    파싱룰 테스트
    
    - **error_id**: 테스트할 에러의 ID
    - **xml_content**: 테스트할 파싱룰 XML 내용
    """
    try:
        result = admin_service.test_parsing_rule(error_id, request.xml_content)
        
        logger.info(f"파싱룰 테스트 API 호출: error_id={error_id}, success={result.get('is_valid')}")
        return TestParsingRuleResponse(**result)
        
    except NotFoundError as e:
        logger.warning(f"파싱룰 테스트 실패: {e.message}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ValidationError as e:
        logger.warning(f"파싱룰 테스트 검증 실패: {e.message}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except ParseRuleTestError as e:
        logger.warning(f"파싱룰 테스트 실행 실패: {e.message}")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.message)
    except BusinessLogicError as e:
        logger.error(f"파싱룰 테스트 비즈니스 로직 오류: {e.message}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message)

@router.post("/{error_id}/submit", response_model=SubmitParsingRuleResponse)
async def submit_parsing_rule(
    error_id: int,
    request: SubmitParsingRuleRequest,
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    파싱룰 전송 (최종 제출)
    
    - **error_id**: 전송할 에러의 ID
    - **xml_content**: 전송할 파싱룰 XML 내용
    
    테스트가 완료된 파싱룰만 전송할 수 있습니다.
    """
    try:
        result = admin_service.submit_parsing_rule(error_id, request.xml_content)
        
        logger.info(f"파싱룰 전송 API 호출: error_id={error_id}, rule_id={result.get('rule_id')}")
        return SubmitParsingRuleResponse(**result)
        
    except NotFoundError as e:
        logger.warning(f"파싱룰 전송 실패: {e.message}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ValidationError as e:
        logger.warning(f"파싱룰 전송 검증 실패: {e.message}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except BusinessLogicError as e:
        logger.warning(f"파싱룰 전송 비즈니스 로직 오류: {e.message}")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.message)

@router.get("/statistics/overview", response_model=ErrorStatisticsResponse)
async def get_error_statistics(
    client_id: Optional[str] = Query(None, description="클라이언트 ID 필터"),
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    에러 통계 조회
    
    - **client_id**: 특정 클라이언트의 통계만 조회 (선택사항)
    """
    try:
        result = admin_service.get_error_statistics(client_id)
        
        logger.info(f"에러 통계 조회 API 호출: client_id={client_id}")
        return ErrorStatisticsResponse(**result)
        
    except BusinessLogicError as e:
        logger.error(f"에러 통계 조회 비즈니스 로직 오류: {e.message}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message)

@router.get("/recent", response_model=RecentErrorsResponse)
async def get_recent_errors(
    hours: int = Query(24, ge=1, le=168, description="조회할 시간 범위 (시간 단위)"),
    limit: int = Query(10, ge=1, le=50, description="최대 조회 개수"),
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    최근 에러 조회
    
    - **hours**: 조회할 시간 범위 (기본값: 24시간, 최대: 168시간)
    - **limit**: 최대 조회 개수 (기본값: 10개, 최대: 50개)
    """
    try:
        result = admin_service.get_recent_errors(hours=hours, limit=limit)
        
        response = RecentErrorsResponse(
            data=result,
            hours=hours,
            count=len(result)
        )
        
        logger.info(f"최근 에러 조회 API 호출: hours={hours}, count={len(result)}")
        return response
        
    except BusinessLogicError as e:
        logger.error(f"최근 에러 조회 비즈니스 로직 오류: {e.message}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message)

@router.patch("/bulk-update-status", response_model=BulkUpdateStatusResponse)
async def bulk_update_error_status(
    request: BulkUpdateStatusRequest,
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    에러 상태 일괄 업데이트
    
    - **error_ids**: 업데이트할 에러 ID 목록
    - **new_status**: 새로운 상태 (ERROR, FIXED, TESTING, COMPLETED)
    """
    try:
        result = admin_service.bulk_update_error_status(request.error_ids, request.new_status)
        
        logger.info(f"에러 상태 일괄 업데이트 API 호출: count={result.get('updated_count')}, status={request.new_status}")
        return BulkUpdateStatusResponse(**result)
        
    except ValidationError as e:
        logger.warning(f"에러 상태 일괄 업데이트 검증 실패: {e.message}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except BusinessLogicError as e:
        logger.error(f"에러 상태 일괄 업데이트 비즈니스 로직 오류: {e.message}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message) 