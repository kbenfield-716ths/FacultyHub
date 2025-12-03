"""
Public service weeks endpoints.
Allows any authenticated faculty to view available weeks.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from pydantic import BaseModel

from backend.models import ServiceWeek, UnavailabilityRequest, ServiceWeekAssignment, get_db
from backend.auth import get_current_user
from backend.models import Faculty

router = APIRouter(prefix="/api/service-weeks", tags=["service-weeks"])


class ServiceWeekPublicResponse(BaseModel):
    """Public view of service week - available to all faculty."""
    id: str
    week_number: int
    label: str
    start_date: str
    end_date: str
    week_type: str
    point_cost_off: int
    point_reward_work: int
    min_staff_required: int
    year: int
    # Stats for faculty to make informed decisions
    request_count: int = 0
    

@router.get("", response_model=List[ServiceWeekPublicResponse])
async def get_service_weeks(
    year: int = 2026,
    current_user: Faculty = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all service availability weeks for a given year.
    Available to any authenticated faculty member.
    """
    weeks = db.query(ServiceWeek).filter(ServiceWeek.year == year).order_by(ServiceWeek.week_number).all()
    
    # Get request counts for each week
    result = []
    for week in weeks:
        request_count = db.query(func.count(UnavailabilityRequest.id)).filter(
            UnavailabilityRequest.week_id == week.id
        ).scalar()
        
        result.append(ServiceWeekPublicResponse(
            id=week.id,
            week_number=week.week_number,
            label=week.label,
            start_date=week.start_date.isoformat(),
            end_date=week.end_date.isoformat(),
            week_type=week.week_type,
            point_cost_off=week.point_cost_off,
            point_reward_work=week.point_reward_work,
            min_staff_required=week.min_staff_required,
            year=week.year,
            request_count=request_count or 0
        ))
    
    return result
