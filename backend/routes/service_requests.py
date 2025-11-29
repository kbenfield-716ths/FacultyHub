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

from backend.models import Faculty, VacationWeek, VacationRequest, get_db
from backend.auth import get_current_user

router = APIRouter(prefix="/api/service-requests", tags=["service-requests"])

# ==========================================
# PYDANTIC MODELS
# ==========================================

class VacationRequestInput(BaseModel):
    """Model for a single vacation request"""
    week_id: str
    status: str  # "unavailable" or "available"
    points_spent: int = 0
    points_earned: int = 0


class VacationRequestSubmit(BaseModel):
    """Model for submitting multiple requests"""
    requests: List[VacationRequestInput]


class VacationRequestResponse(BaseModel):
    """Model for vacation request response"""
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
def submit_vacation_requests(
    data: VacationRequestSubmit,
    current_user: Faculty = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit or update vacation requests for the current faculty member.
    This replaces all existing requests for this faculty member.
    """
    try:
        # Delete existing requests for this faculty
        db.query(VacationRequest).filter(
            VacationRequest.faculty_id == current_user.id
        ).delete()
        
        # Create new requests
        created_requests = []
        for req in data.requests:
            # Verify week exists
            week = db.query(VacationWeek).filter_by(id=req.week_id).first()
            if not week:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Week {req.week_id} not found"
                )
            
            # Validate status
            if req.status not in ["unavailable", "available"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {req.status}"
                )
            
            # Create request
            vacation_request = VacationRequest(
                id=f"VR-{uuid.uuid4().hex[:8].upper()}",
                faculty_id=current_user.id,
                week_id=req.week_id,
                status=req.status,
                points_spent=req.points_spent,
                points_earned=req.points_earned,
                gives_priority=False  # Will be set by admin during draft
            )
            
            db.add(vacation_request)
            created_requests.append(vacation_request)
        
        db.commit()
        
        return {
            "message": f"Successfully submitted {len(created_requests)} requests",
            "total_requests": len(created_requests),
            "faculty_id": current_user.id,
            "faculty_name": current_user.name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit requests: {str(e)}"
        )


@router.get("/my-requests", response_model=List[VacationRequestResponse])
def get_my_requests(
    current_user: Faculty = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all vacation requests for the current faculty member.
    """
    requests = (
        db.query(
            VacationRequest.id,
            VacationRequest.faculty_id,
            Faculty.name.label("faculty_name"),
            VacationRequest.week_id,
            VacationWeek.week_number,
            VacationWeek.label.label("week_label"),
            VacationRequest.status,
            VacationRequest.points_spent,
            VacationRequest.points_earned,
            VacationRequest.created_at
        )
        .join(Faculty, VacationRequest.faculty_id == Faculty.id)
        .join(VacationWeek, VacationRequest.week_id == VacationWeek.id)
        .filter(VacationRequest.faculty_id == current_user.id)
        .order_by(VacationWeek.week_number)
        .all()
    )
    
    return [
        VacationRequestResponse(
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
    Delete all vacation requests for the current faculty member.
    """
    db.query(VacationRequest).filter(
        VacationRequest.faculty_id == current_user.id
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
    requests = db.query(VacationRequest).filter(
        VacationRequest.faculty_id == current_user.id
    ).all()
    
    unavailable_count = sum(1 for r in requests if r.status == "unavailable")
    available_count = sum(1 for r in requests if r.status == "available")
    
    total_spent = sum(r.points_spent for r in requests)
    total_earned = sum(r.points_earned for r in requests)
    
    available_points = current_user.base_points + current_user.bonus_points - total_spent + total_earned
    
    return {
        "faculty_id": current_user.id,
        "faculty_name": current_user.name,
        "base_points": current_user.base_points,
        "bonus_points": current_user.bonus_points,
        "total_points": current_user.base_points + current_user.bonus_points,
        "points_spent": total_spent,
        "points_earned": total_earned,
        "available_points": available_points,
        "weeks_unavailable": unavailable_count,
        "weeks_available": available_count,
        "total_requests": len(requests)
    }
