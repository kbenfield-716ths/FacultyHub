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
from typing import List, Optional, Dict
from pydantic import BaseModel
import uuid

from backend.models import get_db, Faculty, VacationWeek, VacationRequest
from backend.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/admin", tags=["admin-service"])


# ===== REQUEST/RESPONSE MODELS =====

class SpecialWeekConfig(BaseModel):
    """Configuration for a special week period"""
    name: str  # e.g., "Christmas", "Thanksgiving", "ATS Conference"
    date: str  # ISO format date (middle of the week)
    duration_weeks: int = 1  # Number of weeks
    point_cost: int = 15
    point_reward: int = 20


class GenerateWeeksRequest(BaseModel):
    """Request to generate 52 weeks with special period configurations"""
    year: int
    start_date: str  # ISO format: "2026-07-07"
    # Optional flat date fields for convenience (will be converted to special_weeks)
    summer_start: Optional[str] = None
    summer_end: Optional[str] = None
    spring_break: Optional[str] = None
    thanksgiving: Optional[str] = None
    christmas: Optional[str] = None
    ats_conference: Optional[str] = None
    chest_conference: Optional[str] = None
    sccm_conference: Optional[str] = None
    # Or use the structured format
    special_weeks: List[SpecialWeekConfig] = []


class UpdateWeekRequest(BaseModel):
    label: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    week_type: Optional[str] = None
    point_cost_off: Optional[int] = None
    point_reward_work: Optional[int] = None
    min_staff_required: Optional[int] = None


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
    
    weeks = db.query(VacationWeek).filter(VacationWeek.year == year).order_by(VacationWeek.week_number).all()
    
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


@router.patch("/service-weeks/{week_id}")
async def update_service_week_partial(
    week_id: str,
    request: UpdateWeekRequest,
    db: Session = Depends(get_db),
    current_user: Faculty = Depends(require_admin)
):
    """Partially update a service week's details (PATCH for inline editing)"""
    
    week = db.query(VacationWeek).filter(VacationWeek.id == week_id).first()
    if not week:
        raise HTTPException(status_code=404, detail="Week not found")
    
    # Update fields if provided
    if request.label is not None:
        week.label = request.label
    if request.start_date is not None:
        week.start_date = datetime.strptime(request.start_date, "%Y-%m-%d").date()
    if request.end_date is not None:
        week.end_date = datetime.strptime(request.end_date, "%Y-%m-%d").date()
    if request.week_type is not None:
        week.week_type = request.week_type
    if request.point_cost_off is not None:
        week.point_cost_off = request.point_cost_off
    if request.point_reward_work is not None:
        week.point_reward_work = request.point_reward_work
    if request.min_staff_required is not None:
        week.min_staff_required = request.min_staff_required
    
    db.commit()
    db.refresh(week)
    
    return {
        "success": True,
        "week": {
            "id": week.id,
            "week_number": week.week_number,
            "label": week.label,
            "start_date": week.start_date.isoformat(),
            "end_date": week.end_date.isoformat(),
            "week_type": week.week_type,
            "point_cost_off": week.point_cost_off,
            "point_reward_work": week.point_reward_work,
            "min_staff_required": week.min_staff_required
        }
    }


@router.delete("/service-weeks/{week_id}")
async def delete_single_week(
    week_id: str,
    db: Session = Depends(get_db),
    current_user: Faculty = Depends(require_admin)
):
    """Delete a single service availability week"""
    
    week = db.query(VacationWeek).filter(VacationWeek.id == week_id).first()
    if not week:
        raise HTTPException(status_code=404, detail="Week not found")
    
    # Delete associated requests
    db.query(VacationRequest).filter(VacationRequest.week_id == week_id).delete(synchronize_session=False)
    
    # Delete the week
    db.delete(week)
    db.commit()
    
    return {
        "success": True,
        "message": f"Week {week.week_number} deleted"
    }


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
    
    # Parse start date
    start_date = datetime.strptime(request.start_date, "%Y-%m-%d").date()
    
    # Convert flat date fields to special_weeks if provided
    special_weeks = list(request.special_weeks)  # Start with any provided special_weeks
    
    # Add conferences
    if request.ats_conference:
        special_weeks.append(SpecialWeekConfig(
            name="ATS Conference",
            date=request.ats_conference,
            duration_weeks=1,
            point_cost=15,
            point_reward=20
        ))
    
    if request.chest_conference:
        special_weeks.append(SpecialWeekConfig(
            name="CHEST Conference",
            date=request.chest_conference,
            duration_weeks=1,
            point_cost=15,
            point_reward=20
        ))
    
    if request.sccm_conference:
        special_weeks.append(SpecialWeekConfig(
            name="SCCM Conference",
            date=request.sccm_conference,
            duration_weeks=1,
            point_cost=15,
            point_reward=20
        ))
    
    # Add holidays
    if request.spring_break:
        special_weeks.append(SpecialWeekConfig(
            name="Spring Break",
            date=request.spring_break,
            duration_weeks=1,
            point_cost=10,
            point_reward=15
        ))
    
    if request.thanksgiving:
        special_weeks.append(SpecialWeekConfig(
            name="Thanksgiving",
            date=request.thanksgiving,
            duration_weeks=1,
            point_cost=15,
            point_reward=20
        ))
    
    if request.christmas:
        special_weeks.append(SpecialWeekConfig(
            name="Christmas",
            date=request.christmas,
            duration_weeks=2,  # Christmas is 2 weeks
            point_cost=15,
            point_reward=25
        ))
    
    # Parse special weeks into a dict for easy lookup
    special_weeks_by_date: Dict[date, SpecialWeekConfig] = {}
    for special in special_weeks:
        special_date = datetime.strptime(special.date, "%Y-%m-%d").date()
        # For multi-week periods, add all weeks
        for week_offset in range(special.duration_weeks):
            offset_date = special_date + timedelta(weeks=week_offset)
            special_weeks_by_date[offset_date] = special
    
    weeks_created = []
    current_date = start_date
    
    for week_num in range(1, 53):
        end_date = current_date + timedelta(days=6)
        
        # Default values
        week_type = "regular"
        point_cost_off = 5
        point_reward_work = 0
        label = f"Week {week_num} ({current_date.strftime('%b %d')})"
        
        # Check if it's summer (June-August)
        # Use provided summer dates if available, otherwise default to month check
        is_summer = False
        if request.summer_start and request.summer_end:
            summer_start = datetime.strptime(request.summer_start, "%Y-%m-%d").date()
            summer_end = datetime.strptime(request.summer_end, "%Y-%m-%d").date()
            if summer_start <= current_date <= summer_end:
                is_summer = True
        elif current_date.month in [6, 7, 8]:
            is_summer = True
        
        if is_summer:
            week_type = "summer"
            point_cost_off = 7
            point_reward_work = 5
            label = f"Week {week_num} - Summer ({current_date.strftime('%b %d')})"
        
        # Check if this week matches any special week configurations
        # Special weeks override summer designation
        for special_date, special_config in special_weeks_by_date.items():
            # If current week is within 3 days of the special date
            if abs((current_date - special_date).days) <= 3:
                week_type = special_config.name.lower().replace(" ", "_")
                point_cost_off = special_config.point_cost
                point_reward_work = special_config.point_reward
                label = f"Week {week_num} - {special_config.name} ({current_date.strftime('%b %d')})"
                break
        
        # Create week
        week = VacationWeek(
            id=f"W{week_num:02d}-{request.year}",
            week_number=week_num,
            label=label,
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
