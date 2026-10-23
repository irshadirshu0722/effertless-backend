from app.application.use_case.exception import AppError


class TrailPlanNotFoundError(AppError):
    def __init__(self, code="TRAIL_NOT_FOUND", message="Trail not exist", status_code=409):
        super().__init__(code, message, status_code)
