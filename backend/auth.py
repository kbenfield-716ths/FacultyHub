"""
Authentication utilities for faculty login system.
Provides password hashing, session management, and authentication dependencies.

NOTE: Uses bcrypt directly instead of passlib due to version compatibility issues.
"""

from datetime import datetime, timedelta
from typing import Optional
import secrets
import bcrypt

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session

from .models import Faculty, get_db

# HTTP Basic Auth (for initial testing, we'll use sessions in production)
security = HTTPBasic()

# Session storage (in-memory for now, move to Redis for production)
active_sessions = {}


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        print(f"Password verification error: {e}")
        return False


def create_session_token() -> str:
    """Generate a secure random session token."""
    return secrets.token_urlsafe(32)


def create_session(faculty_id: str, faculty_name: str, is_admin: bool, impersonated_by: Optional[str] = None) -> str:
    """Create a new session and return the session token.
    
    Args:
        faculty_id: ID of the faculty member
        faculty_name: Name of the faculty member
        is_admin: Whether the faculty member is an admin
        impersonated_by: Optional faculty ID of the admin who is impersonating this user
    """
    token = create_session_token()
    active_sessions[token] = {
        "faculty_id": faculty_id,
        "faculty_name": faculty_name,
        "is_admin": is_admin,
        "created_at": datetime.utcnow(),
        "last_activity": datetime.utcnow(),
        "impersonated_by": impersonated_by  # Store original admin ID if impersonating
    }
    return token


def get_session(token: str) -> Optional[dict]:
    """Get session data from token."""
    session = active_sessions.get(token)
    if session:
        # Update last activity
        session["last_activity"] = datetime.utcnow()
        
        # Check if session is expired (24 hours)
        if datetime.utcnow() - session["created_at"] > timedelta(hours=24):
            delete_session(token)
            return None
    
    return session


def delete_session(token: str):
    """Delete a session."""
    if token in active_sessions:
        del active_sessions[token]


def authenticate_faculty(faculty_id: str, password: str, db: Session) -> Optional[Faculty]:
    """Authenticate a faculty member by ID and password."""
    faculty = db.query(Faculty).filter_by(id=faculty_id.upper()).first()
    if not faculty:
        return None
    
    if not verify_password(password, faculty.password_hash):
        return None
    
    if not faculty.active:
        return None
    
    return faculty


# ==========================================
# FASTAPI DEPENDENCIES
# ==========================================

async def get_current_user(request: Request, db: Session = Depends(get_db)) -> Faculty:
    """Get the currently authenticated user from session cookie."""
    # Check for session token in cookies
    session_token = request.cookies.get("session_token")
    
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get session data
    session = get_session(session_token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get faculty from database
    faculty = db.query(Faculty).filter_by(id=session["faculty_id"]).first()
    if not faculty or not faculty.active:
        delete_session(session_token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or inactive"
        )
    
    return faculty


async def require_admin(current_user: Faculty = Depends(get_current_user)) -> Faculty:
    """Require that the current user is an admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


async def get_optional_user(request: Request, db: Session = Depends(get_db)) -> Optional[Faculty]:
    """Get the current user if authenticated, None otherwise (no exception)."""
    session_token = request.cookies.get("session_token")
    
    if not session_token:
        return None
    
    session = get_session(session_token)
    if not session:
        return None
    
    faculty = db.query(Faculty).filter_by(id=session["faculty_id"]).first()
    if not faculty or not faculty.active:
        return None
    
    return faculty
