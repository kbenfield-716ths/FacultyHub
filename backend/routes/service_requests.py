"""
Faculty service availability request endpoints.
These allow faculty to submit their unavailable/available weeks.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime
import uuid

from backend.models import Faculty, ServiceWeek, UnavailabilityRequest, get_db
from backend.auth import get_current_user

router = APIRouter(prefix="/api/service-requests", tags=["service-requests"])

# ==========================================
# PYDANTIC MODELS
# ==========================================

class UnavailabilityRequestInput(BaseModel):
    """Model for a single availability request.
    
    Note: points_spent and points_earned are calculated server-side
    based on the week's configuration. Client values are ignored for security.
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
    
    Points are calculated server-side based on week configuration for security.
    """
    try:
        # Delete existing requests for this faculty
        db.query(UnavailabilityRequest).filter(
            UnavailabilityRequest.faculty_id == current_user.id
        ).delete()
        
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
            
            # Calculate points server-side based on week configuration
            # This prevents clients from submitting incorrect point values
            if req.status == "unavailable":
                points_spent = week.point_cost_off
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
                gives_priority=False  # Will be set by admin during draft
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


@router.get("/my-requests", response_model=List[UnavailabilityRequestResponse])
def get_my_requests(
    current_user: Faculty = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all availability requests for the current faculty member.
    """
    requests = (
        db.query(
            UnavailabilityRequest.id,
            UnavailabilityRequest.faculty_id,
            Faculty.name.label("faculty_name"),
            UnavailabilityRequest.week_id,
            ServiceWeek.week_number,
            ServiceWeek.label.label("week_label"),
            UnavailabilityRequest.status,
            UnavailabilityRequest.points_spent,
            UnavailabilityRequest.points_earned,
            UnavailabilityRequest.created_at
        )
        .join(Faculty, UnavailabilityRequest.faculty_id == Faculty.id)
        .join(ServiceWeek, UnavailabilityRequest.week_id == ServiceWeek.id)
        .filter(UnavailabilityRequest.faculty_id == current_user.id)
        .order_by(ServiceWeek.week_number)
        .all()
    )
    
    return [
        UnavailabilityRequestResponse(
            id=r.id,
            faculty_id=r.faculty_id,
            faculty_name=r.faculty_name,
            week_id=r.week_id,
            week_number=r.week_number,
            week_label=r.week_label,
            status=r.status,
            points_spent=r.points_spent,
            points_earned=r.points_earned,
            created_at=r.created_at
        )
        for r in requests
    ]


@router.delete("/my-requests", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_requests(
    current_user: Faculty = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete all availability requests for the current faculty member.
    """
    db.query(UnavailabilityRequest).filter(
        UnavailabilityRequest.faculty_id == current_user.id
    ).delete()
    
    db.commit()
    return None


@router.get("/summary")
def get_my_summary(
    current_user: Faculty = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get summary statistics for the current faculty member.
    """
    # Count requests by status
    requests = db.query(UnavailabilityRequest).filter(
        UnavailabilityRequest.faculty_id == current_user.id
    ).all()
    
    unavailable_count = sum(1 for r in requests if r.status == "unavailable")
    available_count = sum(1 for r in requests if r.status == "available")
    
    total_spent = sum(r.points_spent for r in requests)
    total_earned = sum(r.points_earned for r in requests)
    
    base_points = current_user.base_points
    bonus_points = current_user.bonus_points or 0
    available_points = base_points + bonus_points - total_spent + total_earned
    
    return {
        "faculty_id": current_user.id,
        "faculty_name": current_user.name,
        "base_points": base_points,
        "bonus_points": bonus_points,
        "total_points": base_points + bonus_points,
        "points_spent": total_spent,
        "points_earned": total_earned,
        "available_points": available_points,
        "weeks_unavailable": unavailable_count,
        "weeks_available": available_count,
        "total_requests": len(requests)
    }
