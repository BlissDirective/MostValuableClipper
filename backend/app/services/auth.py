from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

security = HTTPBearer()

# Use admin client only for token validation (auth.get_user is an admin operation)
def _get_admin_client():
    from app.services.database import supabase_admin
    return supabase_admin


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Validate JWT and return the Supabase user object."""
    token = credentials.credentials
    try:
        result = _get_admin_client().auth.get_user(token)
        if not result or not result.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        return result.user
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Optionally validate JWT — returns None if missing/invalid."""
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def get_user_db(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    _user=Depends(get_current_user),  # ensures token is validated first
):
    """FastAPI dependency: returns a SupabaseService scoped to the requesting user.

    All queries via the returned service respect Row Level Security policies,
    so cross-user data access is enforced at the database layer.
    """
    from app.services.database import SupabaseService, get_user_client
    return SupabaseService(get_user_client(credentials.credentials))
