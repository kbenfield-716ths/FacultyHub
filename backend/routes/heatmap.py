# backend/routes/heatmap.py
"""
API routes for heatmap visualization and management.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import date
from pydantic import BaseModel

from ..models import get_db, VacationWeek
from ..heatmap import (
    generate_schedule_year_weeks,
    calculate_full_heatmap,
    calculate_week_pressure,
    update_week_heatmap_data,
    get_heatmap_calendar_data,
    get_week_alternatives,
    analyze_request_patterns,
    snapshot_heatmap,
    upload_historic_data
)

router = APIRouter(prefix="/api/heatmap", tags=["heatmap"])


# ==========================================
# REQUEST/RESPONSE MODELS
# ==========================================

class InitializeYearRequest(BaseModel):
    start_date: str  # ISO format "2025-07-06"


class HistoricDataPoint(BaseModel):
    week_number: int
    request_count: int


class HistoricDataUpload(BaseModel):
    data: List[HistoricDataPoint]


# ==========================================
# ROUTES
# ==========================================

@router.post("/initialize-year")
def initialize_schedule_year(
    request: InitializeYearRequest,
    db: Session = Depends(get_db)
):
    """
    Initialize 52 weeks for the schedule year starting from specified date.
    
    Example: POST with {"start_date": "2025-07-06"}
    """
    try:
        start_date = date.fromisoformat(request.start_date)
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")
    
    # Check if weeks already exist
    existing_count = db.query(VacationWeek).filter(
        VacationWeek.year == start_date.year
    ).count()
    
    if existing_count > 0:
        raise HTTPException(
            400, 
            f"Schedule year {start_date.year} already initialized with {existing_count} weeks. "
            "Delete existing weeks first if you want to reinitialize."
        )
    
    # Generate weeks
    weeks = generate_schedule_year_weeks(start_date, db)
    
    # Add to database
    for week in weeks:
        db.add(week)
    
    db.commit()
    
    return {
        "status": "success",
        "message": f"Initialized {len(weeks)} weeks starting {start_date.isoformat()}",
        "year": start_date.year,
        "weeks_created": len(weeks)
    }


@router.get("/full")
def get_full_heatmap(db: Session = Depends(get_db)):
    """
    Get complete heatmap for all 52 weeks with pressure scores and costs.
    """
    heatmap = calculate_full_heatmap(db)
    
    return {
        "status": "success",
        "heatmap": heatmap,
        "total_weeks": len(heatmap)
    }


@router.get("/calendar")
def get_calendar_heatmap(db: Session = Depends(get_db)):
    """
    Get heatmap data formatted for calendar visualization with monthly groupings.
    """
    calendar_data = get_heatmap_calendar_data(db)
    
    return {
        "status": "success",
        **calendar_data
    }


@router.get("/week/{week_id}")
def get_week_details(week_id: str, db: Session = Depends(get_db)):
    """
    Get detailed information for a specific week including alternatives.
    
    Example: GET /api/heatmap/week/W01
    """
    week = db.query(VacationWeek).filter(VacationWeek.id == week_id).first()
    
    if not week:
        raise HTTPException(404, f"Week {week_id} not found")
    
    # Calculate current metrics
    metrics = calculate_week_pressure(week, db)
    
    # Get alternative weeks
    alternatives = get_week_alternatives(week_id, db, count=3)
    
    return {
        "status": "success",
        "week": metrics,
        "alternatives": alternatives
    }


@router.post("/week/{week_id}/update")
def update_week_metrics(week_id: str, db: Session = Depends(get_db)):
    """
    Recalculate and update heatmap metrics for a specific week.
    Call this after vacation requests are added/removed.
    
    Example: POST /api/heatmap/week/W01/update
    """
    try:
        metrics = update_week_heatmap_data(week_id, db)
        
        return {
            "status": "success",
            "message": f"Updated metrics for {week_id}",
            "metrics": metrics
        }
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/update-all")
def update_all_week_metrics(db: Session = Depends(get_db)):
    """
    Recalculate metrics for all weeks.
    Useful after bulk operations or data imports.
    """
    weeks = db.query(VacationWeek).all()
    updated_count = 0
    
    for week in weeks:
        try:
            update_week_heatmap_data(week.id, db)
            updated_count += 1
        except Exception as e:
            print(f"Error updating {week.id}: {e}")
    
    return {
        "status": "success",
        "message": f"Updated {updated_count} weeks",
        "weeks_updated": updated_count
    }


@router.get("/analysis")
def get_pattern_analysis(db: Session = Depends(get_db)):
    """
    Get analysis of request patterns and trends.
    """
    analysis = analyze_request_patterns(db)
    
    return {
        "status": "success",
        **analysis
    }


@router.post("/snapshot")
def create_heatmap_snapshot(db: Session = Depends(get_db)):
    """
    Take a snapshot of current heatmap state for historical tracking.
    """
    snapshot_heatmap(db)
    
    return {
        "status": "success",
        "message": "Heatmap snapshot created",
        "snapshot_date": date.today().isoformat()
    }


@router.post("/upload-historic")
def upload_historic_request_data(
    upload: HistoricDataUpload,
    db: Session = Depends(get_db)
):
    """
    Upload historic request data to adjust initial point costs.
    
    Example:
    {
        "data": [
            {"week_number": 1, "request_count": 18},
            {"week_number": 2, "request_count": 15},
            {"week_number": 40, "request_count": 16}
        ]
    }
    """
    historic_data = [{"week_number": d.week_number, "request_count": d.request_count} 
                     for d in upload.data]
    
    upload_historic_data(historic_data, db)
    
    return {
        "status": "success",
        "message": f"Uploaded {len(historic_data)} historic data points",
        "records_processed": len(historic_data)
    }


@router.delete("/clear-year/{year}")
def clear_schedule_year(year: int, db: Session = Depends(get_db)):
    """
    Delete all weeks for a specific schedule year.
    Use with caution!
    """
    weeks_deleted = db.query(VacationWeek).filter(
        VacationWeek.year == year
    ).delete()
    
    db.commit()
    
    return {
        "status": "success",
        "message": f"Deleted {weeks_deleted} weeks for year {year}",
        "weeks_deleted": weeks_deleted
    }
