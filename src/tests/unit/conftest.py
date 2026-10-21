from unittest.mock import AsyncMock, Mock

import pytest


@pytest.fixture
def subscription_repo():
    repo = Mock()
    repo.get_active_by_user_id = AsyncMock(return_value=None)
    repo.save = AsyncMock()
    return repo


@pytest.fixture
def plan_repo():
    repo = Mock()
    repo.get_by_code = AsyncMock()
    return repo


@pytest.fixture
def payment_gateway():
    gateway = Mock()
    gateway.create_checkout_session = AsyncMock(
        return_value=("cashfree-sub-123", "checkout-session-123")
    )
    return gateway
