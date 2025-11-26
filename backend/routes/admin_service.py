# backend/routes/admin_service.py
"""
Admin routes for managing service availability weeks.
This manages the 52-week schedule where faculty indicate when they 
are NOT available for regular inpatient service duties.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, date
from typing import List, Optional
from pydantic import BaseModel
import uuid

from backend.models import get_db, Faculty, VacationWeek, VacationRequest
from backend.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/admin", tags=["admin-service"])


# ===== REQUEST/RESPONSE MODELS =====

class GenerateWeeksRequest(BaseModel):
    year: int
    start_date: str  # ISO format: "2026-07-07"
    spring_break: Optional[str] = None
    thanksgiving: Optional[str] = None
    christmas: Optional[str] = None


class ServiceWeekResponse(BaseModel):
    id: str
    week_number: int
    label: str
    start_date: str
    end_date: str
    week_type: str
    point_cost_off: int
    point_reward_work: int
    min_staff_required: int
    request_count: int = 0


# ===== ADMIN ENDPOINTS =====

@router.get("/service-weeks", response_model=List[ServiceWeekResponse])
async def get_service_weeks(
    year: int = 2026,
    db: Session = Depends(get_db),
    current_user: Faculty = Depends(require_admin)
):
    """Get all service availability weeks for a given year"""
    
    weeks = db.query(VacationWeek).filter(VacationWeek.year == year).all()
    
    # Get request counts for each week
    result = []
    for week in weeks:
        request_count = db.query(func.count(VacationRequest.id)).filter(
            VacationRequest.week_id == week.id
        ).scalar()
        
        result.append(ServiceWeekResponse(
            id=week.id,
            week_number=week.week_number,
            label=week.label,
            start_date=week.start_date.isoformat(),
            end_date=week.end_date.isoformat(),
            week_type=week.week_type,
            point_cost_off=week.point_cost_off,
            point_reward_work=week.point_reward_work,
            min_staff_required=week.min_staff_required,
            request_count=request_count
        ))
    
    return result


@router.post("/generate-service-weeks")
async def generate_service_weeks(
    request: GenerateWeeksRequest,
    db: Session = Depends(get_db),
    current_user: Faculty = Depends(require_admin)
):
    """
    Generate 52 weeks for service availability scheduling.
    
    This creates the annual schedule where faculty indicate:
    - Unavailable: Cannot work inpatient service (costs points)
    - Available: Can work if needed (neutral)
    - Requested: Volunteering for holiday coverage (earns bonus points)
    """
    
    # Check if weeks already exist for this year
    existing = db.query(VacationWeek).filter(VacationWeek.year == request.year).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Weeks already exist for {request.year}. Clear them first."
        )
    
    # Parse dates
    start_date = datetime.strptime(request.start_date, "%Y-%m-%d").date()
    spring_break = datetime.strptime(request.spring_break, "%Y-%m-%d").date() if request.spring_break else None
    thanksgiving = datetime.strptime(request.thanksgiving, "%Y-%m-%d").date() if request.thanksgiving else None
    christmas = datetime.strptime(request.christmas, "%Y-%m-%d").date() if request.christmas else None
    
    weeks_created = []
    current_date = start_date
    
    for week_num in range(1, 53):
        end_date = current_date + timedelta(days=6)
        
        # Determine week type and point values
        week_type = "regular"
        point_cost_off = 5
        point_reward_work = 0
        
        # Check if it's a special week
        month = current_date.month
        
        # Summer weeks (June-August): Higher cost, some reward
        if month in [6, 7, 8]:
            week_type = "summer"
            point_cost_off = 7
            point_reward_work = 5
        
        # Spring break
        if spring_break and abs((current_date - spring_break).days) < 7:
            week_type = "spring_break"
            point_cost_off = 12
            point_reward_work = 15
        
        # Thanksgiving
        if thanksgiving and abs((current_date - thanksgiving).days) < 7:
            week_type = "thanksgiving"
            point_cost_off = 15
            point_reward_work = 20
        
        # Christmas (2 weeks)
        if christmas:
            christmas_end = christmas + timedelta(days=14)
            if christmas <= current_date <= christmas_end:
                week_type = "christmas"
                point_cost_off = 15
                point_reward_work = 20
        
        # Create week
        week = VacationWeek(
            id=f"W{week_num:02d}-{request.year}",
            week_number=week_num,
            label=f"Week {week_num} ({current_date.strftime('%b %d')})",
            start_date=current_date,
            end_date=end_date,
            year=request.year,
            week_type=week_type,
            point_cost_off=point_cost_off,
            point_reward_work=point_reward_work,
            min_staff_required=5
        )
        
        db.add(week)
        weeks_created.append(week)
        
        # Move to next week
        current_date = current_date + timedelta(days=7)
    
    db.commit()
    
    return {
        "success": True,
        "weeks_created": len(weeks_created),
        "year": request.year,
        "start_date": request.start_date,
        "end_date": weeks_created[-1].end_date.isoformat()
    }


@router.delete("/service-weeks")
async def clear_service_weeks(
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Faculty = Depends(require_admin)
):
    """
    Clear all service availability weeks and associated requests.
    If year is provided, only clear that year. Otherwise clear all.
    """
    
    if year:
        weeks = db.query(VacationWeek).filter(VacationWeek.year == year).all()
    else:
        weeks = db.query(VacationWeek).all()
    
    week_ids = [w.id for w in weeks]
    
    # Delete all requests for these weeks
    db.query(VacationRequest).filter(VacationRequest.week_id.in_(week_ids)).delete(synchronize_session=False)
    
    # Delete weeks
    db.query(VacationWeek).filter(VacationWeek.id.in_(week_ids)).delete(synchronize_session=False)
    
    db.commit()
    
    return {
        "success": True,
        "weeks_deleted": len(weeks),
        "year": year or "all"
    }


@router.get("/service-requests")
async def get_service_requests(
    year: Optional[int] = None,
    faculty_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Faculty = Depends(require_admin)
):
    """Get all service availability requests with filters"""
    
    query = db.query(VacationRequest).join(VacationWeek).join(Faculty)
    
    if year:
        query = query.filter(VacationWeek.year == year)
    
    if faculty_id:
        query = query.filter(VacationRequest.faculty_id == faculty_id)
    
    requests = query.all()
    
    result = []
    for req in requests:
        result.append({
            "id": req.id,
            "faculty_id": req.faculty_id,
            "faculty_name": req.faculty.name,
            "week_id": req.week_id,
            "week_label": req.week.label,
            "week_number": req.week.week_number,
            "status": req.status,
            "points_spent": req.points_spent,
            "points_earned": req.points_earned,
            "created_at": req.created_at.isoformat()
        })
    
    return result


@router.get("/moonlighting-summary")
async def get_moonlighting_summary(
    db: Session = Depends(get_db),
    current_user: Faculty = Depends(require_admin)
):
    """Get summary statistics for moonlighting periods"""
    
    from backend.models import Month, Shift, Signup, Assignment
    
    months = db.query(Month).all()
    
    result = []
    for month in months:
        shifts = db.query(Shift).filter(Shift.month_id == month.id).all()
        total_shifts = sum(s.slots for s in shifts)
        
        signup_count = db.query(func.count(Signup.id)).join(Shift).filter(
            Shift.month_id == month.id
        ).scalar()
        
        assignment_count = db.query(func.count(Assignment.id)).join(Shift).filter(
            Shift.month_id == month.id
        ).scalar()
        
        result.append({
            "period": f"{month.year}-{month.month:02d}",
            "total_shifts": total_shifts,
            "signups": signup_count,
            "assignments": assignment_count
        })
    
    return result


@router.get("/months")
async def get_months(
    db: Session = Depends(get_db),
    current_user: Faculty = Depends(require_admin)
):
    """Get all moonlighting months"""
    from backend.models import Month
    
    months = db.query(Month).all()
    return [{"id": m.id, "year": m.year, "month": m.month} for m in months]
