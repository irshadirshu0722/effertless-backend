from app.application.use_case.exception import AppError


class PlanNotFoundError(AppError):
    def __init__(self, plan_code: str):
        super().__init__(
            "PLAN_NOT_FOUND", f"Plan with this code{plan_code} not found", status_code=404
        )
