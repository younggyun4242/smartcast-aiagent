"""
애플리케이션 커스텀 예외 클래스
비즈니스 로직에서 발생하는 예외들을 정의
"""

class BaseAppException(Exception):
    """애플리케이션 기본 예외 클래스"""
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class NotFoundError(BaseAppException):
    """리소스를 찾을 수 없는 경우 예외"""
    def __init__(self, message: str = "리소스를 찾을 수 없습니다"):
        super().__init__(message, "NOT_FOUND")

class ValidationError(BaseAppException):
    """데이터 검증 실패 예외"""
    def __init__(self, message: str = "데이터 검증에 실패했습니다"):
        super().__init__(message, "VALIDATION_ERROR")

class BusinessLogicError(BaseAppException):
    """비즈니스 로직 위반 예외"""
    def __init__(self, message: str = "비즈니스 로직 오류가 발생했습니다"):
        super().__init__(message, "BUSINESS_LOGIC_ERROR")

class ParseRuleTestError(BaseAppException):
    """파싱 룰 테스트 실패 예외"""
    def __init__(self, message: str = "파싱 룰 테스트가 실패했습니다"):
        super().__init__(message, "PARSE_RULE_TEST_ERROR")

class ExternalServiceError(BaseAppException):
    """외부 서비스 호출 실패 예외"""
    def __init__(self, message: str = "외부 서비스 호출이 실패했습니다"):
        super().__init__(message, "EXTERNAL_SERVICE_ERROR")

class DatabaseError(BaseAppException):
    """데이터베이스 관련 예외"""
    def __init__(self, message: str = "데이터베이스 오류가 발생했습니다"):
        super().__init__(message, "DATABASE_ERROR") 