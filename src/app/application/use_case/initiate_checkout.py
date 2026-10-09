"""Use case for creating a Cashfree checkout subscription session."""

from dataclasses import dataclass

from app.core.exceptions import PlanNotFoundError
from app.domain.entities.authenticated_user import AuthenticatedUser
from app.ports.subscription import PaymentGateway, PlanRepository


@dataclass(frozen=True, slots=True)
class CheckoutSessionResult:
    subscription_id: str
    payment_link: str
    status: str = "pending"


class InitiateCheckoutUseCase:
    """Creates a subscription checkout session via the payment gateway."""

    def __init__(
        self,
        plan_repo: PlanRepository,
        payment_gateway: PaymentGateway,
    ) -> None:
        self._plan_repo = plan_repo
        self._payment_gateway = payment_gateway

    async def execute(
        self,
        user: AuthenticatedUser,
        plan_code: str,
        return_url: str,
    ) -> CheckoutSessionResult:
        plan = await self._plan_repo.get_by_code(plan_code)
        if not plan or not plan.is_active or plan.is_deleted:
            raise PlanNotFoundError(plan_code)

        subscription_id, payment_link = await self._payment_gateway.create_checkout_session(
            user_id=user.user_id,
            user_email=user.email,
            plan=plan,
            return_url=return_url,
        )

        return CheckoutSessionResult(
            subscription_id=subscription_id,
            payment_link=payment_link,
            status="pending",
        )
