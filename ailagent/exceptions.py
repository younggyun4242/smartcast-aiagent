"""
ailagent 패키지용 예외 클래스들
관리자 API에서 사용되는 예외 정의
"""

class BaseAppException(Exception):
    """기본 애플리케이션 예외"""
    def __init__(self, message: str, error_code: str = "UNKNOWN_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(message)

class NotFoundError(BaseAppException):
    """리소스를 찾을 수 없는 경우"""
    def __init__(self, message: str = "리소스를 찾을 수 없습니다"):
        super().__init__(message, "NOT_FOUND")

class ValidationError(BaseAppException):
    """입력 데이터 검증 실패"""
    def __init__(self, message: str = "입력 데이터가 올바르지 않습니다"):
        super().__init__(message, "VALIDATION_ERROR")

class BusinessLogicError(BaseAppException):
    """비즈니스 로직 오류"""
    def __init__(self, message: str = "비즈니스 로직 처리 중 오류가 발생했습니다"):
        super().__init__(message, "BUSINESS_LOGIC_ERROR") 