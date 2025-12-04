# backend/routes/schedule_routes.py
"""
API routes for inpatient service schedule generation and viewing.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from backend.models import get_db, Faculty
from backend.auth import require_admin
from backend.schedule_generator import generate_schedule, get_schedule_view

router = APIRouter(prefix="/api/admin", tags=["schedule"])


class GenerateScheduleRequest(BaseModel):
    """Request to generate a schedule"""
    year: int = 2026
    clear_existing: bool = True


@router.post("/generate-service-schedule")
async def generate_service_schedule(
    request: GenerateScheduleRequest,
    db: Session = Depends(get_db),
    current_user: Faculty = Depends(require_admin)
):
    """
    Generate inpatient service schedule for the academic year.
    
    This will:
    1. Clear existing assignments (if clear_existing=True)
    2. Assign faculty to services based on their allocations
    3. Respect unavailability requests
    4. Enforce service requirements (MICU=2, APP-ICU=1, Procedures=1, Consults=1)
    5. Allow +/- 1 week flexibility per service
    
    Returns summary with any staffing or capacity issues found.
    """
    try:
        result = generate_schedule(
            db=db,
            year=request.year,
            clear_existing=request.clear_existing
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schedule generation failed: {str(e)}")


@router.get("/service-schedule")
async def get_service_schedule(
    year: int = 2026,
    db: Session = Depends(get_db),
    current_user: Faculty = Depends(require_admin)
):
    """
    Get the current service schedule for viewing.
    
    Returns all weeks with their assignments for each service type.
    """
    try:
        result = get_schedule_view(db=db, year=year)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get schedule: {str(e)}")


@router.delete("/service-schedule")
async def clear_service_schedule(
    year: int = 2026,
    db: Session = Depends(get_db),
    current_user: Faculty = Depends(require_admin)
):
    """
    Clear all service assignments for a year.
    """
    from backend.models import ServiceWeek, ServiceWeekAssignment
    
    weeks = db.query(ServiceWeek).filter(ServiceWeek.year == year).all()
    week_ids = [w.id for w in weeks]
    
    deleted = db.query(ServiceWeekAssignment).filter(
        ServiceWeekAssignment.week_id.in_(week_ids)
    ).delete(synchronize_session=False)
    
    db.commit()
    
    return {
        "success": True,
        "assignments_deleted": deleted,
        "year": year
    }
