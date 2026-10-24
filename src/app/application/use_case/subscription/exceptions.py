from app.application.use_case.exception import AppError


class TrailPlanNotFoundError(AppError):
    def __init__(self, code="TRAIL_NOT_FOUND", message="Trail not exist", status_code=409):
        super().__init__(code, message, status_code)


class AlreadyHaveActiveSubscriptionError(AppError):
    def __init__(
        self,
        code="ALREADY_HAVE_ACTIVE_PLAN",
        message="You already have an active plan for this given plan",
        status_code=409,
    ):
        super().__init__(code, message, status_code)
