"""Autenticação via Entra ID (MSAL). Desabilitável em dev via AUTH_ENABLED=false."""
import os
from dataclasses import dataclass

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer(auto_error=False)

TENANT_ID = os.environ.get("AZURE_AD_TENANT_ID", "")
CLIENT_ID = os.environ.get("AZURE_AD_CLIENT_ID", "")
AUTH_ENABLED = os.environ.get("AUTH_ENABLED", "true").lower() == "true"

_JWKS_URL = f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys"
_jwks_client = jwt.PyJWKClient(_JWKS_URL) if AUTH_ENABLED and TENANT_ID else None


@dataclass
class UserInfo:
    oid: str
    name: str
    email: str


def _mock_user() -> UserInfo:
    """Usuário fake usado quando AUTH_ENABLED=false."""
    return UserInfo(oid="dev-user", name="Dev User", email="dev@localhost")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> UserInfo:
    if not AUTH_ENABLED:
        return _mock_user()

    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token ausente.")

    token = credentials.credentials
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=CLIENT_ID,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado.")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token inválido: {e}")

    return UserInfo(
        oid=payload["oid"],
        name=payload.get("name", ""),
        email=payload.get("preferred_username", ""),
    )
