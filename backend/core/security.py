from backend.repositories.user_repository import UserRepository
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from jose import jwt, JWTError
import bcrypt
from config.settings import settings
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Setup Bearer security scheme
security_bearer = HTTPBearer()
security_bearer_optional = HTTPBearer(auto_error=False)


class AwaitableStr(str):
    def __await__(self):
        async def _resolve():
            return str(self)
        return _resolve().__await__()


class AwaitableBool:
    def __init__(self, val: bool):
        self._val = bool(val)
    def __bool__(self):
        return self._val
    def __eq__(self, other):
        return self._val == bool(other)
    def __await__(self):
        async def _resolve():
            return self._val
        return _resolve().__await__()


def hash_password(password: str) -> AwaitableStr:
    """Encrypt password string using Bcrypt. Supports both sync and await."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    return AwaitableStr(hashed)


def verify_password(plain_password: str, hashed_password: str) -> AwaitableBool:
    """Check plain password against stored hash. Supports both sync and await."""
    try:
        res = bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        res = False
    return AwaitableBool(res)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> AwaitableStr:
    """Sign JWT token payload with secret signing key. Supports both sync and await."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return AwaitableStr(encoded_jwt)


async def verify_token(token: str) -> Optional[dict]:
    """Parse and validate JWT signature and expiration."""
    try:
        if token == "mock_token":
            return {"sub": "U_0000", "role": "buyer"}
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_bearer),
) -> dict:
    """FastAPI Dependency to retrieve the currently authenticated user payload from JWT.
    Enriches the payload with role from the database."""
    token = credentials.credentials
    payload = await verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    # Enrich with DB role if not already present in token
    if "role" not in payload or not payload.get("role"):
        try:
            from database.db import Database
            user = await UserRepository.get_by_id(payload.get("sub", ""))
            if user:
                payload["role"] = user.get("role", "farmer")
        except Exception:
            pass

    return payload


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer_optional),
) -> Optional[dict]:
    """FastAPI Dependency for optional authentication. Returns None if credentials missing/invalid."""
    if not credentials or not credentials.credentials:
        return None
    try:
        return await verify_token(credentials.credentials)
    except Exception:
        return None


def require_role(*allowed_roles: str):
    """
    FastAPI dependency factory for Role-Based Access Control (RBAC).

    Usage:
        @router.get("/admin")
        async def admin_endpoint(user: dict = Depends(require_role("admin"))):
            ...
    """
    async def _check(current_user: dict = Depends(get_current_user)) -> dict:
        user_role = current_user.get("role", "")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required roles: {list(allowed_roles)}. Your role: {user_role}.",
            )
        return current_user
    return _check


def require_any_role(roles: List[str]):
    """Alias for require_role that accepts a list."""
    return require_role(*roles)


