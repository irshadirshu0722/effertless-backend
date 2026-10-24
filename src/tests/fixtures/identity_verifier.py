from unittest.mock import AsyncMock, Mock

import pytest

from app.adapters.services.authentication_service.gcp_identity import (
    GcpIdentityVerifier,
)


@pytest.fixture
def mock_gcp_identity_verifier(auth_user):
    verifier = Mock(spec=GcpIdentityVerifier)

    verifier.verify_token = AsyncMock(return_value=auth_user)

    verifier.sign_in_with_password = AsyncMock(return_value="mock-gcp-id-token-123")

    return verifier
