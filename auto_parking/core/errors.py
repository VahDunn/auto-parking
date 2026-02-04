class AppError(Exception):
    """Базовая ошибка приложения"""


class NotFoundError(AppError):
    def __init__(self, message: str = "Not found"):
        self.message = message
        super().__init__(message)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden"):
        self.message = message
        super().__init__(message)


class ConflictError(AppError):
    def __init__(self, message: str = "Conflict"):
        self.message = message
        super().__init__(message)
