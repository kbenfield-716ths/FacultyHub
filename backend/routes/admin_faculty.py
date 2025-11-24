"""
Admin endpoints for faculty management.
These require admin authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, EmailStr
import hashlib

from models import Faculty, get_db

router = APIRouter(prefix="/api/admin", tags=["admin"])

# ==========================================
# PYDANTIC MODELS
# ==========================================

class FacultyCreate(BaseModel):
    """Model for creating new faculty"""
    id: str  # UVA computing ID
    name: str
    email: EmailStr
    rank: str  # assistant, associate, full
    clinical_effort_pct: int
    base_points: int
    bonus_points: int = 0
    active: bool = True
    is_admin: bool = False


class FacultyUpdate(BaseModel):
    """Model for updating existing faculty"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    rank: Optional[str] = None
    clinical_effort_pct: Optional[int] = None
    base_points: Optional[int] = None
    bonus_points: Optional[int] = None
    active: Optional[bool] = None
    is_admin: Optional[bool] = None


class FacultyResponse(BaseModel):
    """Model for faculty response"""
    id: str
    name: str
    email: str
    rank: str
    clinical_effort_pct: int
    base_points: int
    bonus_points: int
    active: bool
    is_admin: bool
    password_changed: bool
    registered: bool
    
    class Config:
        from_attributes = True


class PasswordReset(BaseModel):
    """Model for resetting faculty password"""
    new_password: str


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_admin(faculty_id: str, db: Session):
    """Verify that the requesting user is an admin"""
    faculty = db.query(Faculty).filter_by(id=faculty_id).first()
    if not faculty or not faculty.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return faculty


# ==========================================
# ENDPOINTS
# ==========================================

@router.get("/faculty", response_model=List[FacultyResponse])
def get_all_faculty(
    admin_id: str,  # From auth middleware
    active_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get all faculty members.
    Requires admin authentication.
    """
    verify_admin(admin_id, db)
    
    query = db.query(Faculty)
    if active_only:
        query = query.filter_by(active=True)
    
    faculty = query.order_by(Faculty.name).all()
    return faculty


@router.get("/faculty/{faculty_id}", response_model=FacultyResponse)
def get_faculty(
    faculty_id: str,
    admin_id: str,  # From auth middleware
    db: Session = Depends(get_db)
):
    """
    Get a specific faculty member by ID.
    Requires admin authentication.
    """
    verify_admin(admin_id, db)
    
    faculty = db.query(Faculty).filter_by(id=faculty_id).first()
    if not faculty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faculty not found"
        )
    
    return faculty


@router.post("/faculty", response_model=FacultyResponse, status_code=status.HTTP_201_CREATED)
def create_faculty(
    faculty_data: FacultyCreate,
    admin_id: str,  # From auth middleware
    db: Session = Depends(get_db)
):
    """
    Create a new faculty member.
    Requires admin authentication.
    """
    verify_admin(admin_id, db)
    
    # Check if faculty ID already exists
    existing = db.query(Faculty).filter_by(id=faculty_data.id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Faculty with ID {faculty_data.id} already exists"
        )
    
    # Check if email already exists
    existing_email = db.query(Faculty).filter_by(email=faculty_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email {faculty_data.email} already in use"
        )
    
    # Validate rank
    valid_ranks = ["assistant", "associate", "full"]
    if faculty_data.rank.lower() not in valid_ranks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid rank. Must be one of: {', '.join(valid_ranks)}"
        )
    
    # Create new faculty with default password
    new_faculty = Faculty(
        id=faculty_data.id,
        name=faculty_data.name,
        email=faculty_data.email,
        rank=faculty_data.rank.lower(),
        clinical_effort_pct=faculty_data.clinical_effort_pct,
        base_points=faculty_data.base_points,
        bonus_points=faculty_data.bonus_points,
        active=faculty_data.active,
        is_admin=faculty_data.is_admin,
        password_hash=hash_password("PCCM2025!"),
        password_changed=False,
        registered=True
    )
    
    db.add(new_faculty)
    db.commit()
    db.refresh(new_faculty)
    
    return new_faculty


@router.patch("/faculty/{faculty_id}", response_model=FacultyResponse)
def update_faculty(
    faculty_id: str,
    faculty_data: FacultyUpdate,
    admin_id: str,  # From auth middleware
    db: Session = Depends(get_db)
):
    """
    Update an existing faculty member.
    Requires admin authentication.
    """
    verify_admin(admin_id, db)
    
    faculty = db.query(Faculty).filter_by(id=faculty_id).first()
    if not faculty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faculty not found"
        )
    
    # Update only provided fields
    update_data = faculty_data.model_dump(exclude_unset=True)
    
    # Validate rank if provided
    if "rank" in update_data:
        valid_ranks = ["assistant", "associate", "full"]
        if update_data["rank"].lower() not in valid_ranks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid rank. Must be one of: {', '.join(valid_ranks)}"
            )
        update_data["rank"] = update_data["rank"].lower()
    
    # Check email uniqueness if updating email
    if "email" in update_data:
        existing = db.query(Faculty).filter(
            Faculty.email == update_data["email"],
            Faculty.id != faculty_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email {update_data['email']} already in use"
            )
    
    for key, value in update_data.items():
        setattr(faculty, key, value)
    
    db.commit()
    db.refresh(faculty)
    
    return faculty


@router.delete("/faculty/{faculty_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_faculty(
    faculty_id: str,
    admin_id: str,  # From auth middleware
    db: Session = Depends(get_db)
):
    """
    Delete a faculty member (soft delete - sets active=False).
    Requires admin authentication.
    """
    verify_admin(admin_id, db)
    
    faculty = db.query(Faculty).filter_by(id=faculty_id).first()
    if not faculty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faculty not found"
        )
    
    # Soft delete
    faculty.active = False
    db.commit()
    
    return None


@router.post("/faculty/{faculty_id}/reset-password", status_code=status.HTTP_200_OK)
def reset_faculty_password(
    faculty_id: str,
    password_data: PasswordReset,
    admin_id: str,  # From auth middleware
    db: Session = Depends(get_db)
):
    """
    Reset a faculty member's password.
    Requires admin authentication.
    """
    verify_admin(admin_id, db)
    
    faculty = db.query(Faculty).filter_by(id=faculty_id).first()
    if not faculty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faculty not found"
        )
    
    # Validate password length
    if len(password_data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )
    
    # Update password
    faculty.password_hash = hash_password(password_data.new_password)
    faculty.password_changed = False  # Force them to change it again
    
    db.commit()
    
    return {"message": f"Password reset for {faculty.name}"}


@router.post("/faculty/{faculty_id}/toggle-admin", response_model=FacultyResponse)
def toggle_admin_status(
    faculty_id: str,
    admin_id: str,  # From auth middleware
    db: Session = Depends(get_db)
):
    """
    Toggle admin status for a faculty member.
    Requires admin authentication.
    """
    verify_admin(admin_id, db)
    
    faculty = db.query(Faculty).filter_by(id=faculty_id).first()
    if not faculty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faculty not found"
        )
    
    # Toggle admin status
    faculty.is_admin = not faculty.is_admin
    db.commit()
    db.refresh(faculty)
    
    return faculty


@router.get("/faculty/stats/summary")
def get_faculty_stats(
    admin_id: str,  # From auth middleware
    db: Session = Depends(get_db)
):
    """
    Get summary statistics about faculty.
    Requires admin authentication.
    """
    verify_admin(admin_id, db)
    
    total = db.query(Faculty).count()
    active = db.query(Faculty).filter_by(active=True).count()
    admins = db.query(Faculty).filter_by(is_admin=True).count()
    
    # Count by rank
    rank_counts = {}
    for rank in ["assistant", "associate", "full"]:
        count = db.query(Faculty).filter_by(rank=rank, active=True).count()
        rank_counts[rank] = count
    
    return {
        "total_faculty": total,
        "active_faculty": active,
        "admin_count": admins,
        "by_rank": rank_counts
    }
