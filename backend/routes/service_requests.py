"""
Faculty service availability request endpoints.
These allow faculty to submit their unavailable/available weeks.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from pydantic import BaseModel
from datetime import datetime
import uuid

from backend.models import Faculty, ServiceWeek, UnavailabilityRequest, get_db
from backend.auth import get_current_user
from backend.email_service import send_unavailability_confirmation
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/service-requests", tags=["service-requests"])

# Constants
MAX_CAPACITY = 17

# ==========================================
# PYDANTIC MODELS
# ==========================================

class UnavailabilityRequestInput(BaseModel):
    """Model for a single availability request.
    
    Note: points_spent and points_earned are calculated server-side
    based on the week's configuration and current demand.
    """
    week_id: str
    status: str  # "unavailable" or "available"
    # These fields are accepted but recalculated server-side for security
    points_spent: int = 0
    points_earned: int = 0


class UnavailabilityRequestSubmit(BaseModel):
    """Model for submitting multiple requests"""
    requests: List[UnavailabilityRequestInput]


class UnavailabilityRequestResponse(BaseModel):
    """Model for availability request response"""
    id: str
    faculty_id: str
    faculty_name: str
    week_id: str
    week_number: int
    week_label: str
    status: str
    points_spent: int
    points_earned: int
    created_at: datetime
    
    class Config:
        from_attributes = True


def calculate_dynamic_cost(base_cost: int, request_count: int) -> int:
    """Calculate dynamic point cost based on current demand."""
    if request_count <= 5:
        return base_cost
    elif request_count <= 10:
        return base_cost + 5
    elif request_count <= 14:
        return base_cost + 10
    elif request_count <= 16:
        return base_cost + 15
    else:
        return base_cost + 20


# ==========================================
# ENDPOINTS
# ==========================================
@router.post("", status_code=status.HTTP_201_CREATED)
def submit_unavailability_requests(
    data: UnavailabilityRequestSubmit,
    current_user: Faculty = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit or update availability requests for the current faculty member.
    This replaces all existing requests for this faculty member.
    
    Points are calculated server-side based on week configuration and
    current demand (dynamic pricing). Enforces 17-person capacity limit.
    """
    try:
        # Delete existing requests for this faculty
        db.query(UnavailabilityRequest).filter(
            UnavailabilityRequest.faculty_id == current_user.id
        ).delete()
        db.flush()
        
        # Track totals for validation
        total_points_spent = 0
        total_points_earned = 0
        
        # Create new requests
        created_requests = []
        for req in data.requests:
            # Verify week exists and get its point configuration
            week = db.query(ServiceWeek).filter_by(id=req.week_id).first()
            if not week:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Week {req.week_id} not found"
                )
            
            # Validate status
            if req.status not in ["unavailable", "available"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {req.status}. Must be 'unavailable' or 'available'"
                )
            
            # Check capacity for unavailable requests
            if req.status == "unavailable":
                # Count current requests for this week (excluding current user)
                current_requests = db.query(func.count(UnavailabilityRequest.id)).filter(
                    UnavailabilityRequest.week_id == req.week_id,
                    UnavailabilityRequest.status == "unavailable"
                ).scalar() or 0
                
                # Enforce capacity limit
                if current_requests >= MAX_CAPACITY:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Week {week.week_number} ({week.label}) is full. Maximum {MAX_CAPACITY} faculty can request this week."
                    )
                
                # Calculate dynamic cost based on current demand
                dynamic_cost = calculate_dynamic_cost(week.point_cost_off, current_requests)
                points_spent = dynamic_cost
                points_earned = 0
            else:  # available (volunteering)
                points_spent = 0
                points_earned = week.point_reward_work
            
            total_points_spent += points_spent
            total_points_earned += points_earned
            
            # Create request with server-calculated points
            unavailability_request = UnavailabilityRequest(
                id=f"VR-{uuid.uuid4().hex[:8].upper()}",
                faculty_id=current_user.id,
                week_id=req.week_id,
                status=req.status,
                points_spent=points_spent,
                points_earned=points_earned,
                gives_priority=False
            )
            
            db.add(unavailability_request)
            created_requests.append(unavailability_request)
        
        # Validate faculty has enough points
        available_points = current_user.base_points + (current_user.bonus_points or 0)
        net_points = available_points - total_points_spent + total_points_earned
        
        if net_points < 0:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient points. You have {available_points} points but need {total_points_spent} for these requests."
            )
        
        db.commit()
        
        # ========== EMAIL CONFIRMATION ==========
        try:
            # Prepare week data for email - only include unavailable requests
            unavailable_weeks = []
            for req in created_requests:
                if req.status == "unavailable":
                    week = db.query(ServiceWeek).filter_by(id=req.week_id).first()
                    if week:
                        unavailable_weeks.append({
                            "week_number": week.week_number,
                            "start_date": week.start_date.isoformat(),
                            "end_date": week.end_date.isoformat()
                        })
            
            # Only send email if there are unavailable weeks
            if unavailable_weeks:
                first_week = db.query(ServiceWeek).filter_by(
                    id=created_requests[0].week_id
                ).first()
                
                week_year = first_week.start_date.year
                week_month = first_week.start_date.month
                
                if week_month >= 7:
                    academic_year = f"{week_year}-{week_year+1}"
                else:
                    academic_year = f"{week_year-1}-{week_year}"
                
                send_unavailability_confirmation(
                    faculty_name=current_user.name,
                    faculty_email=current_user.email,
                    selected_weeks=unavailable_weeks,
                    academic_year=academic_year
                )
                logger.info(f"Unavailability confirmation email sent to {current_user.email}")
        except Exception as e:
            logger.error(f"Failed to send unavailability confirmation email: {e}")
        
        return {
            "message": f"Successfully submitted {len(created_requests)} requests",
            "total_requests": len(created_requests),
            "faculty_id": current_user.id,
            "faculty_name": current_user.name,
            "points_spent": total_points_spent,
            "points_earned": total_points_earned,
            "remaining_points": net_points
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit requests: {str(e)}"
        )
