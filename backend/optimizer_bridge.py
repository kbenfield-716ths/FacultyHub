# backend/optimizer_bridge.py
from collections import defaultdict
from .models import Signup, Shift, Provider

from moonlighter_optimizer import runoptimizer  # you adapt this import


def run_optimizer_for_month(db, month_row: Month, strategy: str, night_slots: int):
    """
    Pull signups for the given Month from the DB, feed them into the
    MoonlighterScheduleOptimizer, and return a list of (Provider, Shift)
    assignments.
    """
    # Load all signups for this month
    rows = (
        db.query(Signup, Shift, Provider)
        .join(Shift, Signup.shift_id == Shift.id)
        .join(Provider, Signup.provider_id == Provider.id)
        .filter(Shift.month_id == month_row.id)
        .all()
    )

    if not rows:
        return []

    # Build per-faculty records for optimizer:
    # faculty_id -> {faculty_id, name, desired_nights, requested_dates(list), priority}
    faculty_records: Dict[str, Dict] = {}

    for signup, shift, provider in rows:
        fid = provider.id
        if fid not in faculty_records:
            faculty_records[fid] = {
                "faculty_id": fid,
                "name": provider.name,
                "desired_nights": signup.desired_nights,
                "requested_dates": [],
                "priority": 1 if provider.is_priority else 2,
            }
        faculty_records[fid]["requested_dates"].append(shift.date.isoformat())

    # lists -> comma-separated strings
    for rec in faculty_records.values():
        unique_dates = sorted(set(rec["requested_dates"]))
        rec["requested_dates"] = ",".join(unique_dates)

    df = pd.DataFrame(list(faculty_records.values()))

    # Run optimizer
    opt = MoonlighterScheduleOptimizer(df, night_slots=night_slots)
    result = opt.optimize(strategy=strategy or "balanced")
    schedule = result.get("schedule", {})

    # Map back to Provider + Shift objects
    shifts_by_date: Dict[str, Shift] = {
        s.date.isoformat(): s for s in month_row.shifts
    }
    providers_by_id: Dict[str, Provider] = {
        p.id: p for p in db.query(Provider).all()
    }

    assignments: List[Tuple[Provider, Shift]] = []

    for date_str, faculty_ids in schedule.items():
        shift = shifts_by_date.get(date_str)
        if not shift:
            continue
        for fid in faculty_ids:
            provider = providers_by_id.get(fid)
            if provider:
                assignments.append((provider, shift))

    return assignments
