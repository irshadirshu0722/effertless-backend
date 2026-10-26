from unittest.mock import AsyncMock, Mock

import pytest


@pytest.fixture
def subscription_repo():
    repo = Mock()
    repo.get_active_by_user_id = AsyncMock(return_value=None)
    repo.has_user_used_trial = AsyncMock(return_value=False)
    repo.get_by_external_id = AsyncMock(return_value=None)
    repo.get_by_id = AsyncMock(return_value=None)
    repo.save = AsyncMock()
    return repo


@pytest.fixture
def plan_repo():
    repo = Mock()
    repo.get_by_code = AsyncMock()
    return repo


@pytest.fixture
def webhook_repo():
    repo = Mock()
    repo.has_been_processed = AsyncMock(return_value=True)
    repo.record_event = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def payment_gateway():
    gateway = Mock()
    gateway.create_checkout_session = AsyncMock(
        return_value=("cashfree-sub-123", "checkout-session-123")
    )
    gateway.cancel_subscription = AsyncMock(return_value=None)
    return gateway
