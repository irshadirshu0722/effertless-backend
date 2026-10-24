import pytest

from app.api.dependencies import (
    get_db_session,
    get_identity_verifier,
    get_payment_gateway,
)
from main import app


@pytest.fixture(autouse=True)
def override_dependencies(
    mock_cashfree_gateway,
    mock_gcp_identity_verifier,
    db_session,
):
    app.dependency_overrides[get_payment_gateway] = lambda: mock_cashfree_gateway
    app.dependency_overrides[get_identity_verifier] = lambda: mock_gcp_identity_verifier

    async def override_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_db_session

    yield

    app.dependency_overrides.pop(get_payment_gateway, None)
    app.dependency_overrides.pop(get_identity_verifier, None)
    app.dependency_overrides.pop(get_db_session, None)
