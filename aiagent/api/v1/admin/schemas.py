"""
관리자 API 스키마
Pydantic 모델을 사용한 요청/응답 데이터 검증
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator

# === 기본 응답 모델 ===

class BaseResponse(BaseModel):
    """기본 응답 모델"""
    success: bool = True
    message: str = ""

class ErrorResponse(BaseModel):
    """에러 응답 모델"""
    success: bool = False
    error_code: str
    message: str
    details: Optional[str] = None

# === 파싱 에러 관련 스키마 ===

class ParsingErrorSchema(BaseModel):
    """파싱 에러 조회 응답 스키마"""
    id: int
    client_id: str
    raw_data: str
    receipt_data: Optional[Dict[str, Any]] = None
    error_message: str
    status: str
    created_at: str
    updated_at: str

class ParsingErrorListResponse(BaseModel):
    """파싱 에러 목록 응답 스키마"""
    data: List[ParsingErrorSchema]
    total: int
    page: int
    limit: int

class ParsingErrorDetailResponse(ParsingErrorSchema):
    """파싱 에러 상세 응답 스키마"""
    pass

# === 파싱룰 관련 스키마 ===

class UpdateParsingRuleRequest(BaseModel):
    """파싱룰 수정 요청 스키마"""
    xml_content: str = Field(..., min_length=1, description="파싱룰 XML 내용")
    
    @validator('xml_content')
    def validate_xml_content(cls, v):
        if not v.strip().startswith('<PARSER>'):
            raise ValueError('XML은 <PARSER> 태그로 시작해야 합니다')
        if not v.strip().endswith('</PARSER>'):
            raise ValueError('XML은 </PARSER> 태그로 끝나야 합니다')
        return v

class UpdateParsingRuleResponse(BaseResponse):
    """파싱룰 수정 응답 스키마"""
    error_id: int
    status: str

class TestParsingRuleRequest(BaseModel):
    """파싱룰 테스트 요청 스키마"""
    xml_content: str = Field(..., min_length=1, description="테스트할 파싱룰 XML 내용")
    
    @validator('xml_content')
    def validate_xml_content(cls, v):
        if not v.strip().startswith('<PARSER>'):
            raise ValueError('XML은 <PARSER> 태그로 시작해야 합니다')
        if not v.strip().endswith('</PARSER>'):
            raise ValueError('XML은 </PARSER> 태그로 끝나야 합니다')
        return v

class TestParsingRuleResponse(BaseResponse):
    """파싱룰 테스트 응답 스키마"""
    result: Dict[str, Any]
    is_valid: bool

class SubmitParsingRuleRequest(BaseModel):
    """파싱룰 전송 요청 스키마"""
    xml_content: str = Field(..., min_length=1, description="전송할 파싱룰 XML 내용")
    
    @validator('xml_content')
    def validate_xml_content(cls, v):
        if not v.strip().startswith('<PARSER>'):
            raise ValueError('XML은 <PARSER> 태그로 시작해야 합니다')
        if not v.strip().endswith('</PARSER>'):
            raise ValueError('XML은 </PARSER> 태그로 끝나야 합니다')
        return v

class SubmitParsingRuleResponse(BaseResponse):
    """파싱룰 전송 응답 스키마"""
    rule_id: int
    error_id: int
    status: str

# === 통계 관련 스키마 ===

class ErrorStatisticsResponse(BaseModel):
    """에러 통계 응답 스키마"""
    ERROR: int
    FIXED: int
    TESTING: int
    COMPLETED: int
    TOTAL: int

class RecentErrorsResponse(BaseModel):
    """최근 에러 응답 스키마"""
    data: List[ParsingErrorSchema]
    hours: int
    count: int

# === 일괄 작업 스키마 ===

class BulkUpdateStatusRequest(BaseModel):
    """에러 상태 일괄 업데이트 요청 스키마"""
    error_ids: List[int] = Field(..., min_items=1, description="업데이트할 에러 ID 목록")
    new_status: str = Field(..., description="새로운 상태")
    
    @validator('new_status')
    def validate_status(cls, v):
        valid_statuses = ["ERROR", "FIXED", "TESTING", "COMPLETED"]
        if v not in valid_statuses:
            raise ValueError(f'상태는 {valid_statuses} 중 하나여야 합니다')
        return v

class BulkUpdateStatusResponse(BaseResponse):
    """에러 상태 일괄 업데이트 응답 스키마"""
    updated_count: int
    new_status: str

# === ML 데이터 관련 스키마 ===

class MLTrainingDataSchema(BaseModel):
    """ML 훈련 데이터 스키마"""
    id: int
    client_id: str
    receipt_data: Dict[str, Any]
    xml_result: str
    parsing_error_id: Optional[int] = None
    created_at: str

class MLTrainingDataListResponse(BaseModel):
    """ML 훈련 데이터 목록 응답 스키마"""
    data: List[MLTrainingDataSchema]
    total: int
    page: int
    limit: int

class MLDataStatisticsResponse(BaseModel):
    """ML 데이터 통계 응답 스키마"""
    total_count: int
    client_counts: Dict[str, int]
    daily_counts: Dict[str, int]
    period_days: Optional[int] = None
    avg_daily_count: float

class MLDataQualityResponse(BaseModel):
    """ML 데이터 품질 응답 스키마"""
    total_count: int
    valid_count: int
    invalid_count: int
    quality_score: float
    quality_level: str

class MLDataExportRequest(BaseModel):
    """ML 데이터 내보내기 요청 스키마"""
    client_id: Optional[str] = None
    limit: int = Field(default=1000, ge=1, le=10000, description="내보낼 데이터 개수")
    format: str = Field(default="json", description="내보내기 형식 (json, csv)")
    
    @validator('format')
    def validate_format(cls, v):
        valid_formats = ["json", "csv"]
        if v.lower() not in valid_formats:
            raise ValueError(f'형식은 {valid_formats} 중 하나여야 합니다')
        return v.lower()

class MLDataExportResponse(BaseModel):
    """ML 데이터 내보내기 응답 스키마"""
    format: str
    data: Any  # JSON 배열 또는 CSV 문자열
    count: int

class MLDataSearchRequest(BaseModel):
    """ML 데이터 검색 요청 스키마"""
    search_term: str = Field(..., min_length=1, description="검색어")
    client_id: Optional[str] = None

class MLDataSearchResponse(BaseModel):
    """ML 데이터 검색 응답 스키마"""
    data: List[MLTrainingDataSchema]
    search_term: str
    count: int
    page: int
    limit: int

# === 공통 쿼리 파라미터 스키마 ===

class PaginationParams(BaseModel):
    """페이징 파라미터"""
    page: int = Field(default=1, ge=1, description="페이지 번호")
    limit: int = Field(default=20, ge=1, le=100, description="페이지당 항목 수")

class ErrorFilterParams(PaginationParams):
    """에러 필터 파라미터"""
    client_id: Optional[str] = Field(None, description="클라이언트 ID")
    status: Optional[str] = Field(None, description="에러 상태")
    
    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            valid_statuses = ["ERROR", "FIXED", "TESTING", "COMPLETED"]
            if v not in valid_statuses:
                raise ValueError(f'상태는 {valid_statuses} 중 하나여야 합니다')
        return v

class MLDataFilterParams(PaginationParams):
    """ML 데이터 필터 파라미터"""
    client_id: Optional[str] = Field(None, description="클라이언트 ID")
    days: Optional[int] = Field(None, ge=1, le=365, description="조회 기간 (일)")

# === 헬스체크 스키마 ===

class HealthCheckResponse(BaseModel):
    """헬스체크 응답 스키마"""
    status: str = "healthy"
    timestamp: str
    version: str = "1.0.0"
    database: str = "connected"
    services: Dict[str, str] = {
        "admin_service": "active",
        "ml_data_service": "active"
    } 