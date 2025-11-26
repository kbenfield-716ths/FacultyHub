# backend/routes/unavailable_periods.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import date

from ..models import SessionLocal, UnavailablePeriod, Provider

router = APIRouter(prefix="/api/unavailable-periods", tags=["unavailable_periods"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===== Pydantic Schemas =====

class UnavailablePeriodCreate(BaseModel):
    provider_id: Optional[str] = None  # None = applies to all/general
    start_date: date
    end_date: date
    label: str

class UnavailablePeriodUpdate(BaseModel):
    start_date: date
    end_date: date
    label: str

class UnavailablePeriodOut(BaseModel):
    id: int
    provider_id: Optional[str]
    start_date: date
    end_date: date
    label: str
    
    class Config:
        from_attributes = True

# ===== Endpoints =====

@router.post("", response_model=UnavailablePeriodOut)
def create_unavailable_period(
    period: UnavailablePeriodCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new unavailable period.
    If provider_id is None, this applies to the entire calendar.
    """
    if period.start_date > period.end_date:
        raise HTTPException(400, "Start date must be before or equal to end date")
    
    # If provider_id is provided, verify it exists
    if period.provider_id:
        provider = db.query(Provider).filter(Provider.id == period.provider_id).first()
        if not provider:
            raise HTTPException(404, f"Provider '{period.provider_id}' not found")
    
    new_period = UnavailablePeriod(
        provider_id=period.provider_id,
        start_date=period.start_date,
        end_date=period.end_date,
        label=period.label
    )
    db.add(new_period)
    db.commit()
    db.refresh(new_period)
    return new_period

@router.get("", response_model=List[UnavailablePeriodOut])
def list_unavailable_periods(
    provider_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all unavailable periods.
    If provider_id is provided, filter by that provider (and shared periods with provider_id=None).
    """
    q = db.query(UnavailablePeriod)
    
    if provider_id:
        # Get both provider-specific and global periods (where provider_id is None)
        q = q.filter(
            (UnavailablePeriod.provider_id == provider_id) |
            (UnavailablePeriod.provider_id == None)
        )
    
    periods = q.order_by(UnavailablePeriod.start_date).all()
    return periods

@router.get("/year/{year}", response_model=List[UnavailablePeriodOut])
def list_unavailable_periods_for_year(
    year: int,
    provider_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all unavailable periods that fall within a given year.
    """
    from datetime import date as date_type
    
    year_start = date_type(year, 1, 1)
    year_end = date_type(year, 12, 31)
    
    q = db.query(UnavailablePeriod).filter(
        (UnavailablePeriod.start_date <= year_end) &
        (UnavailablePeriod.end_date >= year_start)
    )
    
    if provider_id:
        q = q.filter(
            (UnavailablePeriod.provider_id == provider_id) |
            (UnavailablePeriod.provider_id == None)
        )
    
    periods = q.order_by(UnavailablePeriod.start_date).all()
    return periods

@router.put("/{period_id}", response_model=UnavailablePeriodOut)
def update_unavailable_period(
    period_id: int,
    period: UnavailablePeriodUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an unavailable period.
    """
    existing = db.query(UnavailablePeriod).filter(UnavailablePeriod.id == period_id).first()
    if not existing:
        raise HTTPException(404, f"Period {period_id} not found")
    
    if period.start_date > period.end_date:
        raise HTTPException(400, "Start date must be before or equal to end date")
    
    existing.start_date = period.start_date
    existing.end_date = period.end_date
    existing.label = period.label
    
    db.commit()
    db.refresh(existing)
    return existing

@router.delete("/{period_id}")
def delete_unavailable_period(
    period_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete an unavailable period.
    """
    period = db.query(UnavailablePeriod).filter(UnavailablePeriod.id == period_id).first()
    if not period:
        raise HTTPException(404, f"Period {period_id} not found")
    
    db.delete(period)
    db.commit()
    
    return {"status": "ok", "message": f"Period '{period.label}' deleted"}

@router.get("/check/{provider_id}/{date_str}")
def check_unavailable(
    provider_id: str,
    date_str: str,
    db: Session = Depends(get_db)
):
    """
    Check if a specific date is unavailable for a provider.
    Date format: YYYY-MM-DD
    """
    from datetime import date as date_type
    
    try:
        check_date = date_type.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")
    
    # Check both provider-specific and global unavailable periods
    period = db.query(UnavailablePeriod).filter(
        (
            (UnavailablePeriod.provider_id == provider_id) |
            (UnavailablePeriod.provider_id == None)
        ) &
        (UnavailablePeriod.start_date <= check_date) &
        (UnavailablePeriod.end_date >= check_date)
    ).first()
    
    if period:
        return {
            "available": False,
            "period": {
                "id": period.id,
                "label": period.label,
                "start_date": period.start_date,
                "end_date": period.end_date
            }
        }
    
    return {"available": True}
