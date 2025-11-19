# backend/optimizer_bridge.py
import sys
from pathlib import Path
from typing import List, Tuple, Dict

import pandas as pd

from .models import Provider, Month, Shift, Signup

# Add parent directory to path to import moonlighter_optimizer
sys.path.insert(0, str(Path(__file__).parent.parent))
from moonlighter_optimizer import MoonlighterScheduleOptimizer


def run_optimizer_for_month(db, month_row: Month, strategy: str, night_slots: int):
    """
    Pull signups for the given Month from the DB, feed them into the
    MoonlighterScheduleOptimizer, and return a list of (Provider, Shift)
    assignments.
    """
    try:
        # Load all signups for this month, joined with shifts and providers
        rows = (
            db.query(Signup, Shift, Provider)
            .join(Shift, Signup.shift_id == Shift.id)
            .join(Provider, Signup.provider_id == Provider.id)
            .filter(Shift.month_id == month_row.id)
            .all()
        )

        if not rows:
            print(f"[optimizer] No signups found for month {month_row.year}-{month_row.month:02d}")
            return []

        # Build per-provider records in the shape expected by the optimizer:
        # faculty_id, name, desired_nights, requested_dates, priority
        faculty_records: Dict[str, Dict] = {}

        for signup, shift, provider in rows:
            fid = provider.id  # faculty_id
            if fid not in faculty_records:
                faculty_records[fid] = {
                    "faculty_id": fid,
                    "name": provider.name,
                    "desired_nights": signup.desired_nights,
                    "requested_dates": [],
                    # You can later add a true priority field to Provider;
                    # for now, everyone is "medium" priority = 2
                    "priority": 2,
                }
            faculty_records[fid]["requested_dates"].append(shift.date.isoformat())

        print(f"[optimizer] Found {len(faculty_records)} faculty with signups")

        # Deduplicate & convert lists to comma-separated strings
        for rec in faculty_records.values():
            unique_dates = sorted(set(rec["requested_dates"]))
            rec["requested_dates"] = ",".join(unique_dates)

        # Create DataFrame and run the optimizer
        df = pd.DataFrame(list(faculty_records.values()))
        print(f"[optimizer] DataFrame shape: {df.shape}")
        print(f"[optimizer] DataFrame columns: {list(df.columns)}")

        opt = MoonlighterScheduleOptimizer(df, night_slots=night_slots)
        result = opt.optimize(strategy=strategy or "balanced")
        schedule = result.get("schedule", {})

        print(f"[optimizer] Generated schedule for {len(schedule)} nights")

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
                print(f"[optimizer] Warning: No shift found for date {date_str}")
                continue
            for fid in faculty_ids:
                provider = providers_by_id.get(fid)
                if provider:
                    assignments.append((provider, shift))
                else:
                    print(f"[optimizer] Warning: Provider {fid} not found")

        print(f"[optimizer] Created {len(assignments)} assignments")
        return assignments
        
    except Exception as e:
        print(f"[optimizer] ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise
