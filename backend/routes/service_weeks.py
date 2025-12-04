"""
Public service weeks endpoints.
Allows any authenticated faculty to view available weeks with dynamic pricing.
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

# Dynamic pricing tiers
MAX_CAPACITY = 17

def calculate_dynamic_cost(base_cost: int, request_count: int) -> int:
    """Calculate dynamic point cost based on demand.
    
    Pricing tiers:
    0-5 requests:   Base cost
    6-10 requests:  Base + 5
    11-14 requests: Base + 10
    15-16 requests: Base + 15
    17+ requests:   FULL (unavailable)
    """
    if request_count <= 5:
        return base_cost
    elif request_count <= 10:
        return base_cost + 5
    elif request_count <= 14:
        return base_cost + 10
    elif request_count <= 16:
        return base_cost + 15
    else:
        return base_cost + 20  # Full, but show cost


class ServiceWeekPublicResponse(BaseModel):
    """Public view of service week - available to all faculty."""
    id: str
    week_number: int
    label: str
    start_date: str
    end_date: str
    week_type: str
    base_cost: int  # Original base cost
    point_cost_off: int  # Current dynamic cost
    point_reward_work: int
    min_staff_required: int
    year: int
    # Demand/capacity info
    request_count: int = 0
    max_capacity: int = MAX_CAPACITY
    is_full: bool = False
    demand_level: str = "low"  # low, medium, high, critical, full
    spots_remaining: int = MAX_CAPACITY
    

@router.get("", response_model=List[ServiceWeekPublicResponse])
async def get_service_weeks(
    year: int = 2026,
    current_user: Faculty = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all service availability weeks for a given year with dynamic pricing.
    Available to any authenticated faculty member.
    """
    weeks = db.query(ServiceWeek).filter(ServiceWeek.year == year).order_by(ServiceWeek.week_number).all()
    
    # Get request counts for each week (only count "unavailable" status)
    result = []
    for week in weeks:
        request_count = db.query(func.count(UnavailabilityRequest.id)).filter(
            UnavailabilityRequest.week_id == week.id,
            UnavailabilityRequest.status == "unavailable"
        ).scalar() or 0
        
        # Calculate dynamic cost
        dynamic_cost = calculate_dynamic_cost(week.point_cost_off, request_count)
        
        # Determine demand level
        if request_count >= MAX_CAPACITY:
            demand_level = "full"
        elif request_count >= 15:
            demand_level = "critical"
        elif request_count >= 11:
            demand_level = "high"
        elif request_count >= 6:
            demand_level = "medium"
        else:
            demand_level = "low"
        
        spots_remaining = max(0, MAX_CAPACITY - request_count)
        is_full = request_count >= MAX_CAPACITY
        
        result.append(ServiceWeekPublicResponse(
            id=week.id,
            week_number=week.week_number,
            label=week.label,
            start_date=week.start_date.isoformat(),
            end_date=week.end_date.isoformat(),
            week_type=week.week_type,
            base_cost=week.point_cost_off,
            point_cost_off=dynamic_cost,
            point_reward_work=week.point_reward_work,
            min_staff_required=week.min_staff_required,
            year=week.year,
            request_count=request_count,
            max_capacity=MAX_CAPACITY,
            is_full=is_full,
            demand_level=demand_level,
            spots_remaining=spots_remaining
        ))
    
    return result
