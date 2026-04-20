class AppError(Exception):
    """애플리케이션 기본 예외"""
    def __init__(self, message: str, code: str = "UNKNOWN", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)

class DatabaseError(AppError):
    """데이터베이스 관련 예외"""
    def __init__(self, message: str, code: str = "DATABASE_ERROR"):
        super().__init__(message, code, 500)

class ValidationError(AppError):
    """유효성 검증 실패 예외"""
    def __init__(self, message: str, code: str = "VALIDATION_ERROR"):
        super().__init__(message, code, 400)

class NotFoundError(AppError):
    """리소스를 찾을 수 없음 예외"""
    def __init__(self, resource: str, code: str = "NOT_FOUND"):
        super().__init__(f"{resource}을(를) 찾을 수 없습니다", code, 404)