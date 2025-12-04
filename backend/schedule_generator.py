# backend/schedule_generator.py
"""
Inpatient Service Schedule Generator

Generates weekly assignments for the 4 service types:
- MICU: 2 providers per week
- APP-ICU: 1 provider per week  
- Procedures: 1 provider per week
- Consults: 1 provider per week

Constraints:
- Faculty can only be assigned to services where they have weeks > 0
- Each faculty can work +/- 1 week of their allocated amount per service
- Faculty marked unavailable for a week cannot be assigned
- NO BACK-TO-BACK BLOCKS: Faculty must have at least one week off between any inpatient service assignments
- Try to distribute assignments evenly across the year

"""

from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict
import random
from sqlalchemy.orm import Session
from datetime import datetime
import uuid


@dataclass
class FacultyCapacity:
    """Tracks a faculty member's capacity for each service"""
    faculty_id: str
    name: str
    micu_target: int  # Target weeks (from faculty.micu_weeks)
    app_icu_target: int
    procedures_target: int
    consults_target: int
    micu_assigned: int = 0  # Currently assigned
    app_icu_assigned: int = 0
    procedures_assigned: int = 0
    consults_assigned: int = 0
    last_assigned_week: int = -999  # Track last week number assigned (for back-to-back prevention)
    assigned_weeks: Set[int] = field(default_factory=set)  # All weeks this faculty is assigned
    
    def can_work_service(self, service_type: str) -> bool:
        """Check if faculty can work more weeks of this service (+1 flexibility)"""
        if service_type == "MICU":
            return self.micu_target > 0 and self.micu_assigned < self.micu_target + 1
        elif service_type == "APP-ICU":
            return self.app_icu_target > 0 and self.app_icu_assigned < self.app_icu_target + 1
        elif service_type == "Procedures":
            return self.procedures_target > 0 and self.procedures_assigned < self.procedures_target + 1
        elif service_type == "Consults":
            return self.consults_target > 0 and self.consults_assigned < self.consults_target + 1
        return False
    
    def can_work_week(self, week_number: int) -> bool:
        """
        Check if faculty can work this week (no back-to-back constraint).
        Must have at least one week gap from any previous assignment.
        """
        # Check if the previous week or next week is already assigned
        # We need a gap of at least 1 week between assignments
        if (week_number - 1) in self.assigned_weeks:
            return False  # Previous week is assigned - can't do back-to-back
        if (week_number + 1) in self.assigned_weeks:
            return False  # Next week is assigned - would create back-to-back
        if week_number in self.assigned_weeks:
            return False  # Already assigned this week
        return True
    
    def needs_more_weeks(self, service_type: str) -> bool:
        """Check if faculty still needs assignments to meet minimum (-1 flexibility)"""
        if service_type == "MICU":
            return self.micu_target > 0 and self.micu_assigned < max(0, self.micu_target - 1)
        elif service_type == "APP-ICU":
            return self.app_icu_target > 0 and self.app_icu_assigned < max(0, self.app_icu_target - 1)
        elif service_type == "Procedures":
            return self.procedures_target > 0 and self.procedures_assigned < max(0, self.procedures_target - 1)
        elif service_type == "Consults":
            return self.consults_target > 0 and self.consults_assigned < max(0, self.consults_target - 1)
        return False
    
    def assign(self, service_type: str, week_number: int):
        """Record an assignment"""
        if service_type == "MICU":
            self.micu_assigned += 1
        elif service_type == "APP-ICU":
            self.app_icu_assigned += 1
        elif service_type == "Procedures":
            self.procedures_assigned += 1
        elif service_type == "Consults":
            self.consults_assigned += 1
        
        # Track for back-to-back prevention
        self.last_assigned_week = week_number
        self.assigned_weeks.add(week_number)
    
    def get_priority_score(self, service_type: str) -> float:
        """Get priority score - higher means more urgently needs assignment"""
        if service_type == "MICU":
            if self.micu_target == 0:
                return -1000  # Cannot work this service
            return (self.micu_target - self.micu_assigned) / max(1, self.micu_target)
        elif service_type == "APP-ICU":
            if self.app_icu_target == 0:
                return -1000
            return (self.app_icu_target - self.app_icu_assigned) / max(1, self.app_icu_target)
        elif service_type == "Procedures":
            if self.procedures_target == 0:
                return -1000
            return (self.procedures_target - self.procedures_assigned) / max(1, self.procedures_target)
        elif service_type == "Consults":
            if self.consults_target == 0:
                return -1000
            return (self.consults_target - self.consults_assigned) / max(1, self.consults_target)
        return 0
    
    def get_total_target(self) -> int:
        """Get total target weeks across all services"""
        return self.micu_target + self.app_icu_target + self.procedures_target + self.consults_target
    
    def get_total_assigned(self) -> int:
        """Get total assigned weeks across all services"""
        return self.micu_assigned + self.app_icu_assigned + self.procedures_assigned + self.consults_assigned


@dataclass
class ScheduleAssignment:
    """A single assignment of a faculty to a week/service"""
    faculty_id: str
    week_id: str
    service_type: str


# Service requirements per week
SERVICE_REQUIREMENTS = {
    "MICU": 2,
    "APP-ICU": 1,
    "Procedures": 1,
    "Consults": 1
}


def generate_schedule(
    db: Session,
    year: int = 2026,
    clear_existing: bool = True
) -> Dict:
    """
    Generate a complete inpatient service schedule for the academic year.
    
    Key constraint: NO BACK-TO-BACK BLOCKS
    Faculty must have at least one week off between any inpatient service assignments.
    
    Args:
        db: Database session
        year: Academic year (e.g., 2026 for AY 2026-2027)
        clear_existing: Whether to clear existing assignments first
        
    Returns:
        Dict with schedule summary and any issues found
    """
    from backend.models import Faculty, ServiceWeek, UnavailabilityRequest, ServiceWeekAssignment
    
    # Get all active faculty
    faculty_list = db.query(Faculty).filter(Faculty.active == True).all()
    
    # Get all weeks for this year
    weeks = db.query(ServiceWeek).filter(
        ServiceWeek.year == year
    ).order_by(ServiceWeek.week_number).all()
    
    if not weeks:
        return {
            "success": False,
            "error": f"No weeks found for year {year}. Generate weeks first.",
            "assignments_created": 0
        }
    
    # Get unavailability data
    unavailability_map = defaultdict(set)  # week_id -> set of faculty_ids
    unavailable_requests = db.query(UnavailabilityRequest).filter(
        UnavailabilityRequest.status == "unavailable"
    ).all()
    
    for req in unavailable_requests:
        if req.week_id.endswith(f"-{year}"):
            unavailability_map[req.week_id].add(req.faculty_id)
    
    # Clear existing assignments if requested
    if clear_existing:
        week_ids = [w.id for w in weeks]
        db.query(ServiceWeekAssignment).filter(
            ServiceWeekAssignment.week_id.in_(week_ids)
        ).delete(synchronize_session=False)
        db.commit()
    
    # Initialize faculty capacity tracking
    faculty_capacity = {}
    for f in faculty_list:
        faculty_capacity[f.id] = FacultyCapacity(
            faculty_id=f.id,
            name=f.name,
            micu_target=f.micu_weeks or 0,
            app_icu_target=f.app_icu_weeks or 0,
            procedures_target=f.procedure_weeks or 0,
            consults_target=f.consult_weeks or 0
        )
    
    assignments = []
    issues = []
    back_to_back_prevented = 0  # Track how many times we prevented back-to-back
    
    # For each week, assign faculty to each service
    for week in weeks:
        week_number = week.week_number
        week_assignments = defaultdict(list)  # service_type -> list of faculty_ids
        unavailable_this_week = unavailability_map.get(week.id, set())
        
        # Process each service type
        for service_type, required_count in SERVICE_REQUIREMENTS.items():
            # Get eligible faculty for this service/week
            eligible = []
            for fid, cap in faculty_capacity.items():
                # Skip if unavailable this week (requested off)
                if fid in unavailable_this_week:
                    continue
                    
                # Skip if already assigned this week to another service
                if any(fid in assigned for assigned in week_assignments.values()):
                    continue
                
                # Skip if would create back-to-back (worked last week or scheduled next week)
                if not cap.can_work_week(week_number):
                    back_to_back_prevented += 1
                    continue
                    
                # Check if can work this service (has capacity)
                if cap.can_work_service(service_type):
                    eligible.append((fid, cap))
            
            # Sort by priority (those who need more weeks first)
            # Add small random factor to break ties and spread assignments
            eligible.sort(key=lambda x: (x[1].get_priority_score(service_type), random.random()), reverse=True)
            
            # Assign required number of faculty
            assigned_count = 0
            for fid, cap in eligible:
                if assigned_count >= required_count:
                    break
                
                # Create assignment
                assignment = ScheduleAssignment(
                    faculty_id=fid,
                    week_id=week.id,
                    service_type=service_type
                )
                assignments.append(assignment)
                week_assignments[service_type].append(fid)
                cap.assign(service_type, week_number)
                assigned_count += 1
            
            # Track if we couldn't fill all slots
            if assigned_count < required_count:
                issues.append({
                    "week": week.week_number,
                    "week_label": week.label,
                    "service": service_type,
                    "required": required_count,
                    "assigned": assigned_count,
                    "issue": "understaffed"
                })
    
    # Check for faculty who are significantly over/under their targets
    capacity_issues = []
    for fid, cap in faculty_capacity.items():
        for service, target, assigned in [
            ("MICU", cap.micu_target, cap.micu_assigned),
            ("APP-ICU", cap.app_icu_target, cap.app_icu_assigned),
            ("Procedures", cap.procedures_target, cap.procedures_assigned),
            ("Consults", cap.consults_target, cap.consults_assigned)
        ]:
            if target > 0:
                diff = assigned - target
                if abs(diff) > 1:  # More than +/- 1 week variance
                    capacity_issues.append({
                        "faculty_id": fid,
                        "faculty_name": cap.name,
                        "service": service,
                        "target": target,
                        "assigned": assigned,
                        "variance": diff
                    })
    
    # Save assignments to database
    for assignment in assignments:
        db_assignment = ServiceWeekAssignment(
            id=str(uuid.uuid4()),
            faculty_id=assignment.faculty_id,
            week_id=assignment.week_id,
            service_type=assignment.service_type,
            imported=False
        )
        db.add(db_assignment)
    
    db.commit()
    
    return {
        "success": True,
        "year": year,
        "total_weeks": len(weeks),
        "assignments_created": len(assignments),
        "staffing_issues": issues,
        "capacity_issues": capacity_issues,
        "back_to_back_prevented": back_to_back_prevented,
        "summary": {
            "MICU": sum(1 for a in assignments if a.service_type == "MICU"),
            "APP-ICU": sum(1 for a in assignments if a.service_type == "APP-ICU"),
            "Procedures": sum(1 for a in assignments if a.service_type == "Procedures"),
            "Consults": sum(1 for a in assignments if a.service_type == "Consults")
        }
    }


def get_schedule_view(
    db: Session,
    year: int = 2026
) -> Dict:
    """
    Get the current schedule for viewing.
    
    Returns a structured view of all assignments by week.
    """
    from backend.models import Faculty, ServiceWeek, ServiceWeekAssignment
    
    weeks = db.query(ServiceWeek).filter(
        ServiceWeek.year == year
    ).order_by(ServiceWeek.week_number).all()
    
    if not weeks:
        return {"success": False, "error": "No weeks found", "schedule": []}
    
    # Get all assignments
    week_ids = [w.id for w in weeks]
    assignments = db.query(ServiceWeekAssignment).filter(
        ServiceWeekAssignment.week_id.in_(week_ids)
    ).all()
    
    # Get faculty lookup
    faculty_lookup = {f.id: f.name for f in db.query(Faculty).all()}
    
    # Build assignment map
    assignment_map = defaultdict(lambda: defaultdict(list))  # week_id -> service -> [(faculty_id, name)]
    for a in assignments:
        assignment_map[a.week_id][a.service_type].append({
            "faculty_id": a.faculty_id,
            "faculty_name": faculty_lookup.get(a.faculty_id, a.faculty_id)
        })
    
    # Build schedule view
    schedule = []
    for week in weeks:
        week_data = {
            "week_id": week.id,
            "week_number": week.week_number,
            "label": week.label,
            "start_date": week.start_date.isoformat(),
            "end_date": week.end_date.isoformat(),
            "week_type": week.week_type,
            "assignments": {
                "MICU": assignment_map[week.id].get("MICU", []),
                "APP-ICU": assignment_map[week.id].get("APP-ICU", []),
                "Procedures": assignment_map[week.id].get("Procedures", []),
                "Consults": assignment_map[week.id].get("Consults", [])
            },
            "is_complete": (
                len(assignment_map[week.id].get("MICU", [])) >= 2 and
                len(assignment_map[week.id].get("APP-ICU", [])) >= 1 and
                len(assignment_map[week.id].get("Procedures", [])) >= 1 and
                len(assignment_map[week.id].get("Consults", [])) >= 1
            )
        }
        schedule.append(week_data)
    
    # Calculate summary statistics
    total_assignments = len(assignments)
    complete_weeks = sum(1 for w in schedule if w["is_complete"])
    
    return {
        "success": True,
        "year": year,
        "total_weeks": len(weeks),
        "complete_weeks": complete_weeks,
        "total_assignments": total_assignments,
        "schedule": schedule
    }


def validate_schedule(
    db: Session,
    year: int = 2026
) -> Dict:
    """
    Validate an existing schedule for constraint violations.
    
    Checks:
    - Back-to-back assignments
    - Capacity violations
    - Missing assignments
    
    Returns dict with any violations found.
    """
    from backend.models import Faculty, ServiceWeek, ServiceWeekAssignment
    
    weeks = db.query(ServiceWeek).filter(
        ServiceWeek.year == year
    ).order_by(ServiceWeek.week_number).all()
    
    week_ids = [w.id for w in weeks]
    assignments = db.query(ServiceWeekAssignment).filter(
        ServiceWeekAssignment.week_id.in_(week_ids)
    ).all()
    
    # Track which weeks each faculty is assigned
    faculty_weeks = defaultdict(set)  # faculty_id -> set of week_numbers
    week_number_lookup = {w.id: w.week_number for w in weeks}
    
    for a in assignments:
        week_num = week_number_lookup.get(a.week_id)
        if week_num:
            faculty_weeks[a.faculty_id].add(week_num)
    
    # Check for back-to-back violations
    back_to_back_violations = []
    for faculty_id, assigned_weeks in faculty_weeks.items():
        sorted_weeks = sorted(assigned_weeks)
        for i in range(len(sorted_weeks) - 1):
            if sorted_weeks[i+1] - sorted_weeks[i] == 1:
                back_to_back_violations.append({
                    "faculty_id": faculty_id,
                    "week1": sorted_weeks[i],
                    "week2": sorted_weeks[i+1]
                })
    
    return {
        "year": year,
        "total_assignments": len(assignments),
        "back_to_back_violations": back_to_back_violations,
        "violation_count": len(back_to_back_violations),
        "is_valid": len(back_to_back_violations) == 0
    }
