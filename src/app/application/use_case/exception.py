class AppError(Exception):
    def __init__(
        self,
        code: str = "INTERNAL_SERVER_ERROR",
        message: str = "An unexpected error occurred.",
        status_code: int = 500,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)
