"""DEPRECATED: Use backend.core.security instead. This file exists for backward compatibility."""

from backend.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    verify_token,
    get_current_user,
    get_current_user_optional,
    require_role,
    require_any_role,
    security_bearer
)

