from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.services.auth import get_current_user, supabase

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class MeResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    subscription_tier: str = "free"
    autonomy_mode: str = "approveEach"
    onboarding_completed: bool = False
    created_at: Optional[str] = None


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest):
    """Register a new user with Supabase Auth."""
    try:
        response = supabase.auth.sign_up({
            "email": data.email,
            "password": data.password,
            "options": {
                "data": {
                    "full_name": data.full_name or ""
                }
            }
        })

        if not response.session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed — user may already exist or email confirmation required"
            )

        user = response.user
        session = response.session

        return AuthResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_in=session.expires_in,
            user={
                "id": user.id,
                "email": user.email,
                "full_name": user.user_metadata.get("full_name", "") if user.user_metadata else ""
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration error: {str(e)}"
        )


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest):
    """Authenticate a user with Supabase Auth."""
    try:
        response = supabase.auth.sign_in_with_password({
            "email": data.email,
            "password": data.password
        })

        if not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        user = response.user
        session = response.session

        return AuthResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_in=session.expires_in,
            user={
                "id": user.id,
                "email": user.email,
                "full_name": user.user_metadata.get("full_name", "") if user.user_metadata else ""
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        # Supabase auth errors come as generic exceptions
        error_msg = str(e).lower()
        if "invalid login" in error_msg or "invalid credentials" in error_msg or "user not found" in error_msg or "auth" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login error: {str(e)}"
        )


@router.post("/refresh", response_model=AuthResponse)
async def refresh(data: RefreshRequest):
    """Refresh an access token using a refresh token."""
    try:
        response = supabase.auth.refresh_session(data.refresh_token)

        if not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )

        user = response.user
        session = response.session

        return AuthResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_in=session.expires_in,
            user={
                "id": user.id,
                "email": user.email,
                "full_name": user.user_metadata.get("full_name", "") if user.user_metadata else ""
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Refresh error: {str(e)}"
        )


@router.post("/logout")
async def logout(user=Depends(get_current_user)):
    """Sign out the current user."""
    try:
        # We can't easily revoke the token server-side with Supabase
        # The client should also clear the token from storage
        return {"success": True, "message": "Signed out successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout error: {str(e)}"
        )


@router.get("/me", response_model=MeResponse)
async def get_me(user=Depends(get_current_user)):
    """Get the current authenticated user's profile."""
    return MeResponse(
        id=user.id,
        email=user.email,
        full_name=user.user_metadata.get("full_name") if user.user_metadata else None,
        avatar_url=user.user_metadata.get("avatar_url") if user.user_metadata else None,
        subscription_tier=user.user_metadata.get("subscription_tier", "free") if user.user_metadata else "free",
        autonomy_mode=user.user_metadata.get("autonomy_mode", "approveEach") if user.user_metadata else "approveEach",
        onboarding_completed=user.user_metadata.get("onboarding_completed", False) if user.user_metadata else False,
        created_at=user.created_at if hasattr(user, 'created_at') else None
    )
