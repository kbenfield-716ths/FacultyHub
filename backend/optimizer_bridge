# backend/optimizer_bridge.py
from collections import defaultdict
from .models import Signup, Shift, Provider

from .moonlighter_optimizer import run_optimizer  # you adapt this import


def run_optimizer_for_month(db, month_row, strategy: str, night_slots: int):
    signups = (
        db.query(Signup)
        .join(Shift, Signup.shift_id == Shift.id)
        .join(Provider, Signup.provider_id == Provider.id)
        .filter(Shift.month_id == month_row.id)
        .all()
    )

    # Build structure like your CSV had:
    # provider_id -> { "name": ..., "desired": ..., "dates": [...], "locked_dates": [...] }
    fac = defaultdict(lambda: {"name": None, "desired": 0, "dates": [], "locked": []})

    for su in signups:
        p = su.provider
        s = su.shift
        f = fac[p.id]
        f["name"] = p.name
        f["desired"] = su.desired_nights  # assuming same each row
        f["dates"].append(s.date)
        if su.locked:
            f["locked"].append(s.date)

    # Now call your existing optimizer with this data structure
    # Stub: you fill in how run_optimizer works now
    assignments = run_optimizer(fac, strategy=strategy, night_slots=night_slots)

    # Return list of (Provider, Shift)
    # where assignments is e.g. list of (provider_id, date)
    provider_by_id = {p.id: p for p in db.query(Provider).all()}
    shift_by_date = {s.date: s for s in month_row.shifts}
    result = [
        (provider_by_id[pid], shift_by_date[d])
        for (pid, d) in assignments
    ]
    return result
