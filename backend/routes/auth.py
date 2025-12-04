"""
Authentication endpoints for login, logout, and user management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from backend.models import Faculty, get_db
from backend.auth import (
    authenticate_faculty,
    hash_password,
    create_session,
    delete_session,
    get_current_user,
    get_optional_user
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ==========================================
# PYDANTIC MODELS
# ==========================================

class LoginRequest(BaseModel):
    """Login credentials - accepts 'username' which maps to faculty_id."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response."""
    message: str
    faculty_id: str
    faculty_name: str
    is_admin: bool


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    current_password: str
    new_password: str


class FacultyInfo(BaseModel):
    """Faculty information subset."""
    faculty_id: str
    faculty_name: str
    email: str
    is_admin: bool
    rank: str
    password_changed: bool
    base_points: int
    bonus_points: int
    clinical_effort_pct: int
    
    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """Current user information wrapped in faculty object."""
    faculty: FacultyInfo


# ==========================================
# ENDPOINTS
# ==========================================

@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Authenticate faculty member and create session.
    Returns session cookie.
    
    The 'username' field is used as the faculty_id for lookup.
    """
    # Authenticate user (username is the faculty_id)
    faculty = authenticate_faculty(
        credentials.username,
        credentials.password,
        db
    )
    
    if not faculty:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid faculty ID or password"
        )
    
    # Create session
    session_token = create_session(
        faculty.id,
        faculty.name,
        faculty.is_admin
    )
    
    # Set session cookie (httponly for security)
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        max_age=86400,  # 24 hours
        samesite="lax"
    )
    
    return LoginResponse(
        message="Login successful",
        faculty_id=faculty.id,
        faculty_name=faculty.name,
        is_admin=faculty.is_admin
    )


@router.post("/logout")
async def logout(request: Request, response: Response):
    """
    Logout current user and destroy session.
    """
    session_token = request.cookies.get("session_token")
    
    if session_token:
        delete_session(session_token)
    
    # Clear session cookie
    response.delete_cookie("session_token")
    
    return {"message": "Logout successful"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Faculty = Depends(get_current_user)
):
    """
    Get information about the currently authenticated user.
    Returns nested structure with 'faculty' wrapper for frontend compatibility.
    """
    return UserResponse(
        faculty=FacultyInfo(
            faculty_id=current_user.id,
            faculty_name=current_user.name,
            email=current_user.email,
            is_admin=current_user.is_admin,
            rank=current_user.rank,
            password_changed=current_user.password_changed,
            base_points=current_user.base_points,
            bonus_points=current_user.bonus_points or 0,
            clinical_effort_pct=current_user.clinical_effort_pct
        )
    )


@router.get("/check")
async def check_auth(
    request: Request,
    current_user: Optional[Faculty] = Depends(get_optional_user)
):
    if current_user:
        # Check if impersonating
        session_token = request.cookies.get("session_token")
        from backend.auth import get_session
        session = get_session(session_token) if session_token else None
        impersonated_by = session.get("impersonated_by") if session else None
        
        return {
            "authenticated": True,
            "faculty_id": current_user.id,
            "faculty_name": current_user.name,
            "is_admin": current_user.is_admin,
            "is_impersonating": bool(impersonated_by)
        }
    else:
        return {"authenticated": False}

@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: Faculty = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change the current user's password.
    """
    # Verify current password
    from backend.auth import verify_password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    if len(password_data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )
    
    # Update password
    current_user.password_hash = hash_password(password_data.new_password)
    current_user.password_changed = True
    
    db.commit()
    
    return {"message": "Password changed successfully"}
