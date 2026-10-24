from unittest.mock import AsyncMock, Mock

import pytest

from app.adapters.services.payment_gateway.cashfree import CashfreeSubscriptionAdapter


@pytest.fixture
def mock_cashfree_gateway():
    gateway = Mock(spec=CashfreeSubscriptionAdapter)

    gateway.verify_webhook_signature = Mock(return_value=True)

    gateway.create_checkout_session = AsyncMock(
        return_value=("cashfree-sub-123", "checkout-session-123")
    )
    gateway.cancel_subscription = AsyncMock(return_value=True)
    gateway.create_plan = AsyncMock(return_value=True)
    gateway.delete_plan = AsyncMock(return_value=True)

    return gateway
