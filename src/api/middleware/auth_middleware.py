"""
Supabase JWT verification middleware.
Validates the Authorization: Bearer <token> header on protected routes
and injects the verified user_id into request state.
"""

from __future__ import annotations

import jwt
from fastapi import Request, Response
from jwt import PyJWKClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.config.logging_config import get_logger

logger = get_logger(__name__)

PROTECTED_PATHS = {"/query", "/upload", "/ingest"}
PUBLIC_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}


class SupabaseAuthMiddleware(BaseHTTPMiddleware):
    """Verify Supabase JWT tokens on protected routes."""

    def __init__(
        self,
        app: ASGIApp,
        jwt_secret: str = "",
        supabase_url: str = "",
    ) -> None:
        super().__init__(app)
        self.jwt_secret = jwt_secret
        self.jwks_client: PyJWKClient | None = None
        if supabase_url:
            jwks_url = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
            self.jwks_client = PyJWKClient(jwks_url, cache_keys=True)

    def _verify_token(self, token: str) -> dict:
        header = jwt.get_unverified_header(token)
        algorithm = header.get("alg", "")

        # New Supabase projects sign user tokens with ES256 + JWKS
        if algorithm == "ES256" and self.jwks_client is not None:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256"],
                options={"verify_aud": False},
            )

        # Legacy HS256 symmetric secret
        if not self.jwt_secret:
            raise ValueError("No JWT verification method configured")

        return jwt.decode(
            token,
            self.jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path.rstrip("/") or "/"

        if path in PUBLIC_PATHS or not any(
            path.startswith(p) for p in PROTECTED_PATHS
        ):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return Response(
                content='{"detail":"Authentication required. Please sign in."}',
                status_code=401,
                media_type="application/json",
            )

        token = auth_header.split(" ", 1)[1]

        try:
            payload = self._verify_token(token)
            user_id = payload.get("sub")
            if not user_id:
                raise ValueError("No user ID in token")

            request.state.user_id = user_id

        except jwt.ExpiredSignatureError:
            return Response(
                content='{"detail":"Session expired. Please sign in again."}',
                status_code=401,
                media_type="application/json",
            )
        except Exception as exc:
            logger.warning(f"JWT verification failed: {exc}")
            return Response(
                content='{"detail":"Invalid authentication token."}',
                status_code=401,
                media_type="application/json",
            )

        return await call_next(request)
