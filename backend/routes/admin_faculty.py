"""
Admin endpoints for faculty management.
These require admin authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel, EmailStr

from backend.models import Faculty, ServiceWeekAssignment, ServiceWeek, UnavailabilityRequest, get_db
from backend.auth import require_admin, hash_password, create_session
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request

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
    moonlighter: bool = False
    micu_weeks: int = 0
    app_icu_weeks: int = 0
    procedure_weeks: int = 0
    consult_weeks: int = 0


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
    moonlighter: Optional[bool] = None
    micu_weeks: Optional[int] = None
    app_icu_weeks: Optional[int] = None
    procedure_weeks: Optional[int] = None
    consult_weeks: Optional[int] = None


class ServiceAssignmentSummary(BaseModel):
    """Summary of a faculty member's service assignments"""
    MICU: int = 0
    APP_ICU: int = 0
    Procedures: int = 0
    Consults: int = 0
    total: int = 0


class FacultyResponse(BaseModel):
    """Model for faculty response with service assignments"""
    id: str
    name: str
    email: str
    rank: str
    clinical_effort_pct: int
    base_points: int
    bonus_points: int
    total_points: int
    active: bool
    is_admin: bool
    password_changed: bool
    registered: bool
    # Service week commitments (expected weeks per year)
    moonlighter: bool
    micu_weeks: int
    app_icu_weeks: int
    procedure_weeks: int
    consult_weeks: int
    # Actual service assignments (weeks worked)
    service_weeks: ServiceAssignmentSummary
    
    class Config:
        from_attributes = True


class PasswordReset(BaseModel):
    """Model for resetting faculty password"""
    new_password: str


# ==========================================
# ENDPOINTS
# ==========================================

@router.get("/faculty", response_model=List[FacultyResponse])
def get_all_faculty(
    active_only: bool = False,
    admin_user: Faculty = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get all faculty members with their points and service week assignments.
    Requires admin authentication.
    """
    query = db.query(Faculty)
    if active_only:
        query = query.filter_by(active=True)
    
    faculty_list = query.order_by(Faculty.name).all()
    
    # Build response with service assignments
    result = []
    for faculty in faculty_list:
        # Count service assignments by type
        assignments = db.query(
            ServiceWeekAssignment.service_type,
            func.count(ServiceWeekAssignment.id).label('count')
        ).filter(
            ServiceWeekAssignment.faculty_id == faculty.id
        ).group_by(ServiceWeekAssignment.service_type).all()
        
        # Build service summary
        service_weeks = ServiceAssignmentSummary()
        total = 0
        for service_type, count in assignments:
            total += count
            if service_type == "MICU":
                service_weeks.MICU = count
            elif service_type == "APP-ICU":
                service_weeks.APP_ICU = count
            elif service_type == "Procedures":
                service_weeks.Procedures = count
            elif service_type == "Consults":
                service_weeks.Consults = count
        
        service_weeks.total = total
        
        result.append(FacultyResponse(
            id=faculty.id,
            name=faculty.name,
            email=faculty.email,
            rank=faculty.rank,
            clinical_effort_pct=faculty.clinical_effort_pct,
            base_points=faculty.base_points,
            bonus_points=faculty.bonus_points,
            total_points=faculty.base_points + faculty.bonus_points,
            active=faculty.active,
            is_admin=faculty.is_admin,
            password_changed=faculty.password_changed,
            registered=faculty.registered,
            moonlighter=faculty.moonlighter,
            micu_weeks=faculty.micu_weeks,
            app_icu_weeks=faculty.app_icu_weeks,
            procedure_weeks=faculty.procedure_weeks,
            consult_weeks=faculty.consult_weeks,
            service_weeks=service_weeks
        ))
    
    return result


@router.get("/faculty/{faculty_id}", response_model=FacultyResponse)
def get_faculty(
    faculty_id: str,
    admin_user: Faculty = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get a specific faculty member by ID with their service assignments.
    Requires admin authentication.
    """
    faculty = db.query(Faculty).filter_by(id=faculty_id).first()
    if not faculty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faculty not found"
        )
    
    # Count service assignments by type
    assignments = db.query(
        ServiceWeekAssignment.service_type,
        func.count(ServiceWeekAssignment.id).label('count')
    ).filter(
        ServiceWeekAssignment.faculty_id == faculty.id
    ).group_by(ServiceWeekAssignment.service_type).all()
    
    # Build service summary
    service_weeks = ServiceAssignmentSummary()
    total = 0
    for service_type, count in assignments:
        total += count
        if service_type == "MICU":
            service_weeks.MICU = count
        elif service_type == "APP-ICU":
            service_weeks.APP_ICU = count
        elif service_type == "Procedures":
            service_weeks.Procedures = count
        elif service_type == "Consults":
            service_weeks.Consults = count
    
    service_weeks.total = total
    
    return FacultyResponse(
        id=faculty.id,
        name=faculty.name,
        email=faculty.email,
        rank=faculty.rank,
        clinical_effort_pct=faculty.clinical_effort_pct,
        base_points=faculty.base_points,
        bonus_points=faculty.bonus_points,
        total_points=faculty.base_points + faculty.bonus_points,
        active=faculty.active,
        is_admin=faculty.is_admin,
        password_changed=faculty.password_changed,
        registered=faculty.registered,
        moonlighter=faculty.moonlighter,
        micu_weeks=faculty.micu_weeks,
        app_icu_weeks=faculty.app_icu_weeks,
        procedure_weeks=faculty.procedure_weeks,
        consult_weeks=faculty.consult_weeks,
        service_weeks=service_weeks
    )


@router.post("/faculty", response_model=FacultyResponse, status_code=status.HTTP_201_CREATED)
def create_faculty(
    faculty_data: FacultyCreate,
    admin_user: Faculty = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new faculty member.
    Requires admin authentication.
    """
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
        moonlighter=faculty_data.moonlighter,
        micu_weeks=faculty_data.micu_weeks,
        app_icu_weeks=faculty_data.app_icu_weeks,
        procedure_weeks=faculty_data.procedure_weeks,
        consult_weeks=faculty_data.consult_weeks,
        password_hash=hash_password("PCCM2025!"),
        password_changed=False,
        registered=True
    )
    
    db.add(new_faculty)
    db.commit()
    db.refresh(new_faculty)
    
    # Return with empty service weeks
    return FacultyResponse(
        id=new_faculty.id,
        name=new_faculty.name,
        email=new_faculty.email,
        rank=new_faculty.rank,
        clinical_effort_pct=new_faculty.clinical_effort_pct,
        base_points=new_faculty.base_points,
        bonus_points=new_faculty.bonus_points,
        total_points=new_faculty.base_points + new_faculty.bonus_points,
        active=new_faculty.active,
        is_admin=new_faculty.is_admin,
        password_changed=new_faculty.password_changed,
        registered=new_faculty.registered,
        moonlighter=new_faculty.moonlighter,
        micu_weeks=new_faculty.micu_weeks,
        app_icu_weeks=new_faculty.app_icu_weeks,
        procedure_weeks=new_faculty.procedure_weeks,
        consult_weeks=new_faculty.consult_weeks,
        service_weeks=ServiceAssignmentSummary()
    )


@router.patch("/faculty/{faculty_id}", response_model=FacultyResponse)
def update_faculty(
    faculty_id: str,
    faculty_data: FacultyUpdate,
    admin_user: Faculty = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update an existing faculty member.
    Requires admin authentication.
    """
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
    
    # Get service assignments
    assignments = db.query(
        ServiceWeekAssignment.service_type,
        func.count(ServiceWeekAssignment.id).label('count')
    ).filter(
        ServiceWeekAssignment.faculty_id == faculty.id
    ).group_by(ServiceWeekAssignment.service_type).all()
    
    service_weeks = ServiceAssignmentSummary()
    total = 0
    for service_type, count in assignments:
        total += count
        if service_type == "MICU":
            service_weeks.MICU = count
        elif service_type == "APP-ICU":
            service_weeks.APP_ICU = count
        elif service_type == "Procedures":
            service_weeks.Procedures = count
        elif service_type == "Consults":
            service_weeks.Consults = count
    service_weeks.total = total
    
    return FacultyResponse(
        id=faculty.id,
        name=faculty.name,
        email=faculty.email,
        rank=faculty.rank,
        clinical_effort_pct=faculty.clinical_effort_pct,
        base_points=faculty.base_points,
        bonus_points=faculty.bonus_points,
        total_points=faculty.base_points + faculty.bonus_points,
        active=faculty.active,
        is_admin=faculty.is_admin,
        password_changed=faculty.password_changed,
        registered=faculty.registered,
        moonlighter=faculty.moonlighter,
        micu_weeks=faculty.micu_weeks,
        app_icu_weeks=faculty.app_icu_weeks,
        procedure_weeks=faculty.procedure_weeks,
        consult_weeks=faculty.consult_weeks,
        service_weeks=service_weeks
    )


@router.delete("/faculty/{faculty_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_faculty(
    faculty_id: str,
    admin_user: Faculty = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a faculty member (soft delete - sets active=False).
    Requires admin authentication.
    """
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
    admin_user: Faculty = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Reset a faculty member's password.
    Requires admin authentication.
    """
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
    admin_user: Faculty = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Toggle admin status for a faculty member.
    Requires admin authentication.
    """
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
    
    # Get service assignments
    assignments = db.query(
        ServiceWeekAssignment.service_type,
        func.count(ServiceWeekAssignment.id).label('count')
    ).filter(
        ServiceWeekAssignment.faculty_id == faculty.id
    ).group_by(ServiceWeekAssignment.service_type).all()
    
    service_weeks = ServiceAssignmentSummary()
    total = 0
    for service_type, count in assignments:
        total += count
        if service_type == "MICU":
            service_weeks.MICU = count
        elif service_type == "APP-ICU":
            service_weeks.APP_ICU = count
        elif service_type == "Procedures":
            service_weeks.Procedures = count
        elif service_type == "Consults":
            service_weeks.Consults = count
    service_weeks.total = total
    
    return FacultyResponse(
        id=faculty.id,
        name=faculty.name,
        email=faculty.email,
        rank=faculty.rank,
        clinical_effort_pct=faculty.clinical_effort_pct,
        base_points=faculty.base_points,
        bonus_points=faculty.bonus_points,
        total_points=faculty.base_points + faculty.bonus_points,
        active=faculty.active,
        is_admin=faculty.is_admin,
        password_changed=faculty.password_changed,
        registered=faculty.registered,
        moonlighter=faculty.moonlighter,
        micu_weeks=faculty.micu_weeks,
        app_icu_weeks=faculty.app_icu_weeks,
        procedure_weeks=faculty.procedure_weeks,
        consult_weeks=faculty.consult_weeks,
        service_weeks=service_weeks
    )


@router.get("/faculty/stats/summary")
def get_faculty_stats(
    admin_user: Faculty = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get summary statistics about faculty.
    Requires admin authentication.
    """
    total = db.query(Faculty).count()
    active = db.query(Faculty).filter_by(active=True).count()
    admins = db.query(Faculty).filter_by(is_admin=True).count()
    moonlighters = db.query(Faculty).filter_by(moonlighter=True, active=True).count()
    
    # Count by rank
    rank_counts = {}
    for rank in ["assistant", "associate", "full"]:
        count = db.query(Faculty).filter_by(rank=rank, active=True).count()
        rank_counts[rank] = count
    
    return {
        "total_faculty": total,
        "active_faculty": active,
        "admin_count": admins,
        "moonlighter_count": moonlighters,
        "by_rank": rank_counts
    }


# ==========================================
# TESTING UTILITIES
# ==========================================

@router.post("/impersonate/{faculty_id}")
async def impersonate_faculty(
    faculty_id: str,
    response: Response,
    admin_user: Faculty = Depends(require_admin),
    db: Session = Depends(get_db)
):
    faculty = db.query(Faculty).filter_by(id=faculty_id).first()
    if not faculty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faculty not found"
        )
    
    # Create session with impersonation tracking
    session_token = create_session(
        faculty.id,
        faculty.name,
        faculty.is_admin,
        impersonated_by=admin_user.id  # Store original admin ID
    )
    
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        max_age=86400,
        samesite="lax"
    )
    
    return {
        "success": True,
        "message": f"Now logged in as {faculty.name}",
        "faculty_id": faculty.id,
        "faculty_name": faculty.name,
        "is_admin": faculty.is_admin
    }
@router.post("/return-to-admin")
async def return_to_admin(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """Return from impersonation back to original admin account."""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    from backend.auth import get_session
    session = get_session(session_token)
    if not session or not session.get("impersonated_by"):
        raise HTTPException(status_code=400, detail="Not currently impersonating")
    
    # Get the original admin
    admin = db.query(Faculty).filter_by(id=session["impersonated_by"]).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Original admin not found")
    
    # Create new session as admin
    new_token = create_session(admin.id, admin.name, admin.is_admin)
    
    response.set_cookie(
        key="session_token",
        value=new_token,
        httponly=True,
        max_age=86400,
        samesite="lax"
    )
    
    return {"success": True, "message": f"Returned to {admin.name}"}

@router.post("/reset/points")
async def reset_all_points(
    admin_user: Faculty = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Reset all faculty bonus points to 0.
    Keeps base points intact.
    Admin only - for testing cycles.
    """
    faculty_list = db.query(Faculty).filter_by(active=True).all()
    
    reset_count = 0
    for faculty in faculty_list:
        faculty.bonus_points = 0
        reset_count += 1
    
    db.commit()
    
    return {
        "success": True,
        "faculty_reset": reset_count,
        "message": f"Reset bonus points for {reset_count} faculty members"
    }


@router.post("/reset/requests")
async def reset_all_requests(
    year: Optional[int] = None,
    admin_user: Faculty = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Clear all unavailability requests.
    If year provided, only clear that year.
    Admin only - for testing cycles.
    """
    if year:
        # Get week IDs for this year
        week_ids = [w.id for w in db.query(ServiceWeek).filter_by(year=year).all()]
        deleted = db.query(UnavailabilityRequest).filter(
            UnavailabilityRequest.week_id.in_(week_ids)
        ).delete(synchronize_session=False)
    else:
        deleted = db.query(UnavailabilityRequest).delete(synchronize_session=False)
    
    db.commit()
    
    return {
        "success": True,
        "requests_deleted": deleted,
        "year": year or "all",
        "message": f"Deleted {deleted} unavailability requests" + (f" for {year}" if year else "")
    }


@router.post("/reset/all")
async def reset_everything(
    year: Optional[int] = None,
    admin_user: Faculty = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Complete reset for testing:
    - Clear all unavailability requests
    - Reset all bonus points to 0
    Admin only - for starting fresh test cycles.
    """
    # Reset points
    faculty_list = db.query(Faculty).filter_by(active=True).all()
    faculty_count = 0
    for faculty in faculty_list:
        faculty.bonus_points = 0
        faculty_count += 1
    
    # Clear requests
    if year:
        week_ids = [w.id for w in db.query(ServiceWeek).filter_by(year=year).all()]
        requests_deleted = db.query(UnavailabilityRequest).filter(
            UnavailabilityRequest.week_id.in_(week_ids)
        ).delete(synchronize_session=False)
    else:
        requests_deleted = db.query(UnavailabilityRequest).delete(synchronize_session=False)
    
    db.commit()
    
    return {
        "success": True,
        "faculty_reset": faculty_count,
        "requests_deleted": requests_deleted,
        "year": year or "all",
        "message": f"Complete reset: {faculty_count} faculty, {requests_deleted} requests cleared"
    }
