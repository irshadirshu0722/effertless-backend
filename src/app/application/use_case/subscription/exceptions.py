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


class InvalidWebhookSignatureError(AppError):
    def __init__(
        self,
        code="INVALID_WEBHOOK_SIGNATURE",
        message="Invalid signature",
        status_code=401,
    ):
        super().__init__(code, message, status_code)


class UnknownSubscriptionError(AppError):
    def __init__(
        self,
        code="UNKNOWN_SUBSCRIPTION",
        message="Invalid Subscription id",
        status_code=404,
    ):
        super().__init__(code, message, status_code)
