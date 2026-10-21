"""Authentication backend for SQLAdmin using Firebase/GCP Identity Platform JWT claims."""

from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import Response

from app.core.exceptions import AppError
from app.ports.services.authentication import IdentityVerifier


class AdminAuth(AuthenticationBackend):
    """Secures SQLAdmin dashboard by validating tokens and requiring JWT claim role: admin."""

    def __init__(self, secret_key: str, verifier: IdentityVerifier) -> None:
        super().__init__(secret_key=secret_key)
        self._verifier = verifier

    async def login(self, request: Request) -> Response | bool:
        """Validate credentials from login form."""
        form = await request.form()
        token = str(form.get("token") or "").strip()
        email = str(form.get("username") or form.get("email") or "").strip()
        password = str(form.get("password") or "").strip()

        try:
            id_token: str | None = None
            if token:
                id_token = token
            elif email and password:
                try:
                    id_token = await self._verifier.sign_in_with_password(email, password)
                except Exception:
                    id_token = password
            elif password and not email:
                id_token = password

            if not id_token:
                return False

            user = await self._verifier.verify_token(id_token)
            # Admin is identified by JWT payload: role == "admin"
            # If not exist or role == "user", deny permission
            if user.claims.get("role") != "admin":
                return False

            request.session.update({"token": id_token, "user_id": user.user_id})
            return True
        except (AppError, Exception):
            return False

    async def logout(self, request: Request) -> Response | bool:
        """Clear user session on logout."""
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> Response | bool:
        """Check if request has a valid admin session or Bearer token."""
        token = request.session.get("token")
        if not token:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split("Bearer ", 1)[1].strip()

        if not token:
            return False

        try:
            user = await self._verifier.verify_token(token)
            return user.claims.get("role") == "admin"
        except (AppError, Exception):
            return False
