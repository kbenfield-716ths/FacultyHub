# backend/heatmap.py
"""
Heatmap calculation and visualization for service unavailability scheduling.
Calculates dynamic point costs based on request pressure for each week.
"""

from datetime import date, timedelta
from typing import Dict, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from .models import VacationWeek, VacationRequest, Faculty, WeekHeatmapHistory
import math


# ==========================================
# WEEK GENERATION
# ==========================================

def generate_schedule_year_weeks(start_date: date, db: Session) -> List[VacationWeek]:
    """
    Generate 52 weeks for the schedule year starting from start_date.
    
    Args:
        start_date: First day of first week (e.g., July 6, 2025)
        db: Database session
    
    Returns:
        List of VacationWeek objects
    """
    weeks = []
    current_date = start_date
    
    for week_num in range(1, 53):
        week_id = f"W{week_num:02d}"
        end_date = current_date + timedelta(days=6)
        
        # Determine week type and initial characteristics
        week_type, point_cost, pressure = classify_week(week_num, current_date)
        
        week = VacationWeek(
            id=week_id,
            week_number=week_num,
            label=f"Week {week_num} ({current_date.strftime('%b %d')})",
            start_date=current_date,
            end_date=end_date,
            year=start_date.year,
            week_type=week_type,
            point_cost_off=point_cost,
            point_reward_work=0,  # Can be set later for high-demand weeks
            min_staff_required=5,  # Default; adjustable
            current_requests=0,
            max_capacity=20,  # Will be calculated based on faculty pool
            pressure_score=pressure
        )
        
        weeks.append(week)
        current_date = end_date + timedelta(days=1)
    
    return weeks


def classify_week(week_num: int, start_date: date) -> Tuple[str, int, float]:
    """
    Classify a week and assign initial point cost based on predicted demand.
    
    Args:
        week_num: Week number (1-52)
        start_date: First day of the week
    
    Returns:
        Tuple of (week_type, point_cost, initial_pressure_score)
    """
    month = start_date.month
    day = start_date.day
    
    # High demand periods with preset costs
    # Summer (first 6 weeks: July 6 - Aug 16)
    if week_num <= 6:
        return ("summer", 40, 0.85)
    
    # Spring Break (first week of April, typically week 40)
    # Approximate: April 1 is ~week 39-40 depending on year
    if 39 <= week_num <= 40:
        return ("spring_break", 35, 0.75)
    
    # Christmas (last 2 weeks of December, typically weeks 25-26)
    # December starts around week 23
    if 25 <= week_num <= 26:
        return ("christmas", 30, 0.70)
    
    # Thanksgiving (4th week of November, typically week 21)
    if 21 <= week_num <= 21:
        return ("thanksgiving", 25, 0.60)
    
    # Regular weeks
    return ("regular", 5, 0.2)


# ==========================================
# HEATMAP CALCULATION
# ==========================================

def calculate_week_pressure(week: VacationWeek, db: Session) -> Dict:
    """
    Calculate pressure metrics for a single week.
    
    Args:
        week: VacationWeek object
        db: Database session
    
    Returns:
        Dictionary with pressure metrics
    """
    # Count current unavailability requests
    requests_count = db.query(func.count(VacationRequest.id)).filter(
        VacationRequest.week_id == week.id,
        VacationRequest.status == "unavailable"
    ).scalar() or 0
    
    # Calculate theoretical capacity
    total_faculty = db.query(func.count(Faculty.id)).filter(
        Faculty.active == True
    ).scalar() or 20
    
    required_coverage = week.min_staff_required
    max_unavailable = total_faculty - required_coverage
    
    # Pressure score (0.0 = no pressure, 1.0 = maximum pressure)
    if max_unavailable <= 0:
        pressure = 1.0
    else:
        pressure = min(requests_count / max_unavailable, 1.0)
    
    # Calculate dynamic point cost
    base_cost = 5
    max_multiplier = 10
    
    # Non-linear scaling (quadratic) makes high-demand weeks much more expensive
    multiplier = 1 + (max_multiplier - 1) * (pressure ** 2)
    dynamic_cost = int(base_cost * multiplier)
    
    # Status category
    if pressure < 0.3:
        status = "low"
    elif pressure < 0.6:
        status = "medium"
    elif pressure < 0.9:
        status = "high"
    else:
        status = "critical"
    
    return {
        "week_id": week.id,
        "week_number": week.week_number,
        "label": week.label,
        "start_date": week.start_date.isoformat(),
        "end_date": week.end_date.isoformat(),
        "week_type": week.week_type,
        "requests_count": requests_count,
        "max_capacity": max_unavailable,
        "required_coverage": required_coverage,
        "pressure_score": round(pressure, 3),
        "point_cost": dynamic_cost,
        "status": status,
        "spots_remaining": max(max_unavailable - requests_count, 0)
    }


def calculate_full_heatmap(db: Session) -> List[Dict]:
    """
    Calculate heatmap for all 52 weeks.
    
    Returns:
        List of week pressure dictionaries
    """
    weeks = db.query(VacationWeek).order_by(VacationWeek.week_number).all()
    
    heatmap = []
    for week in weeks:
        week_data = calculate_week_pressure(week, db)
        heatmap.append(week_data)
    
    return heatmap


def update_week_heatmap_data(week_id: str, db: Session) -> Dict:
    """
    Recalculate and update heatmap data for a specific week.
    
    Args:
        week_id: Week identifier (e.g., "W01")
        db: Database session
    
    Returns:
        Updated week metrics
    """
    week = db.query(VacationWeek).filter(VacationWeek.id == week_id).first()
    if not week:
        raise ValueError(f"Week {week_id} not found")
    
    # Calculate new metrics
    metrics = calculate_week_pressure(week, db)
    
    # Update week record
    week.current_requests = metrics["requests_count"]
    week.pressure_score = metrics["pressure_score"]
    week.point_cost_off = metrics["point_cost"]
    
    db.commit()
    
    return metrics


def snapshot_heatmap(db: Session):
    """
    Take a snapshot of current heatmap state for historical tracking.
    
    Args:
        db: Database session
    """
    snapshot_date = date.today()
    weeks = db.query(VacationWeek).all()
    
    for week in weeks:
        metrics = calculate_week_pressure(week, db)
        
        history = WeekHeatmapHistory(
            week_id=week.id,
            snapshot_date=snapshot_date,
            requests_count=metrics["requests_count"],
            capacity=metrics["max_capacity"],
            pressure_score=metrics["pressure_score"],
            point_cost=metrics["point_cost"]
        )
        db.add(history)
    
    db.commit()


# ==========================================
# VISUALIZATION DATA
# ==========================================

def get_heatmap_calendar_data(db: Session) -> Dict:
    """
    Get heatmap data formatted for calendar visualization.
    
    Returns:
        Dictionary with calendar-formatted heatmap data
    """
    heatmap = calculate_full_heatmap(db)
    
    # Group weeks by month for calendar display
    months = {}
    for week_data in heatmap:
        start_date = date.fromisoformat(week_data["start_date"])
        month_key = start_date.strftime("%Y-%m")
        
        if month_key not in months:
            months[month_key] = {
                "month_name": start_date.strftime("%B %Y"),
                "weeks": []
            }
        
        months[month_key]["weeks"].append(week_data)
    
    return {
        "heatmap": heatmap,
        "by_month": months,
        "summary": {
            "total_weeks": len(heatmap),
            "low_demand": len([w for w in heatmap if w["status"] == "low"]),
            "medium_demand": len([w for w in heatmap if w["status"] == "medium"]),
            "high_demand": len([w for w in heatmap if w["status"] == "high"]),
            "critical_demand": len([w for w in heatmap if w["status"] == "critical"])
        }
    }


def get_week_alternatives(week_id: str, db: Session, count: int = 3) -> List[Dict]:
    """
    Find alternative low-cost weeks near a requested high-cost week.
    
    Args:
        week_id: Week being requested
        count: Number of alternatives to return
        db: Database session
    
    Returns:
        List of alternative week suggestions
    """
    target_week = db.query(VacationWeek).filter(VacationWeek.id == week_id).first()
    if not target_week:
        return []
    
    # Get all weeks with their metrics
    heatmap = calculate_full_heatmap(db)
    
    # Find low-pressure weeks within +/- 4 weeks
    target_num = target_week.week_number
    alternatives = []
    
    for week_data in heatmap:
        week_num = week_data["week_number"]
        
        # Skip the target week itself
        if week_num == target_num:
            continue
        
        # Check if within range and low pressure
        if abs(week_num - target_num) <= 4 and week_data["status"] in ["low", "medium"]:
            alternatives.append(week_data)
    
    # Sort by pressure (lowest first), then by proximity
    alternatives.sort(key=lambda w: (w["pressure_score"], abs(w["week_number"] - target_num)))
    
    return alternatives[:count]


# ==========================================
# HISTORICAL ANALYSIS
# ==========================================

def analyze_request_patterns(db: Session) -> Dict:
    """
    Analyze historical patterns in request behavior.
    
    Returns:
        Dictionary with pattern analysis
    """
    heatmap = calculate_full_heatmap(db)
    
    # Categorize weeks
    chronic_high = [w for w in heatmap if w["pressure_score"] > 0.7]
    moderate = [w for w in heatmap if 0.3 <= w["pressure_score"] <= 0.7]
    low_demand = [w for w in heatmap if w["pressure_score"] < 0.3]
    
    return {
        "chronic_high_demand": chronic_high,
        "moderate_demand": moderate,
        "low_demand": low_demand,
        "total_requests": sum(w["requests_count"] for w in heatmap),
        "average_pressure": sum(w["pressure_score"] for w in heatmap) / len(heatmap) if heatmap else 0,
        "total_spots_available": sum(w["spots_remaining"] for w in heatmap)
    }


def upload_historic_data(historic_requests: List[Dict], db: Session):
    """
    Upload historic request data to adjust initial point costs.
    
    Args:
        historic_requests: List of dicts with keys: week_number, request_count
        db: Database session
    
    Example:
        historic_requests = [
            {"week_number": 1, "request_count": 18},
            {"week_number": 2, "request_count": 15},
            ...
        ]
    """
    for record in historic_requests:
        week_num = record["week_number"]
        request_count = record["request_count"]
        
        week = db.query(VacationWeek).filter(
            VacationWeek.week_number == week_num
        ).first()
        
        if week:
            # Update current requests to reflect historic data
            week.current_requests = request_count
            
            # Recalculate pressure and cost
            metrics = calculate_week_pressure(week, db)
            week.pressure_score = metrics["pressure_score"]
            week.point_cost_off = metrics["point_cost"]
    
    db.commit()
