# backend/app.py
from datetime import date
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .models import (
    SessionLocal,
    init_db,
    Provider,
    Month,
    Shift,
    Signup,
    Assignment,
)
from .optimizer_bridge import run_optimizer_for_month

app = FastAPI()

# Allow calls from your GitHub Pages site
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later you can lock this to your GitHub Pages URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class SignupPayload(BaseModel):
    provider_id: str
    provider_name: str
    month: str            # "2025-12"
    desired_nights: int
    dates: List[date]     # ["2025-12-01", ...]
    locked_dates: List[date] = []


@app.post("/api/signup")
def save_signup(payload: SignupPayload, db: Session = Depends(get_db)):
    # Ensure provider
    provider = db.query(Provider).get(payload.provider_id)
    if not provider:
        provider = Provider(id=payload.provider_id, name=payload.provider_name)
        db.add(provider)

    year, month = map(int, payload.month.split("-"))
    month_row = (
        db.query(Month)
        .filter(Month.year == year, Month.month == month)
        .first()
    )
    if not month_row:
        month_row = Month(year=year, month=month)
        db.add(month_row)
        db.flush()

    # Ensure shifts exist for dates
    existing_shifts = {
        s.date: s for s in db.query(Shift).filter(Shift.month_id == month_row.id)
    }

    selected_dates = set(payload.dates) | set(payload.locked_dates)

    for d in selected_dates:
        if d not in existing_shifts:
            s = Shift(month_id=month_row.id, date=d, slots=1)
            db.add(s)
            db.flush()
            existing_shifts[d] = s

    # Clear old signups for this provider+month
    shift_ids = [s.id for s in existing_shifts.values()]
    db.query(Signup).filter(
        Signup.provider_id == payload.provider_id,
        Signup.shift_id.in_(shift_ids),
    ).delete(synchronize_session=False)

    # Write new signups
    locked_set = set(payload.locked_dates)
    for d in payload.dates:
        su = Signup(
            provider_id=payload.provider_id,
            shift_id=existing_shifts[d].id,
            desired_nights=payload.desired_nights,
            locked=d in locked_set,
        )
        db.add(su)

    db.commit()
    return {"status": "ok"}


# -------- Admin endpoint to see signups --------

class AdminSignupOut(BaseModel):
    provider_id: str
    provider_name: str
    date: date
    month: str            # "YYYY-MM"
    desired_nights: int
    locked: bool


@app.get("/api/admin/signups", response_model=List[AdminSignupOut])
def list_signups(
    month: Optional[str] = None,  # "YYYY-MM" or omitted
    db: Session = Depends(get_db),
):
    # Join Signup -> Shift -> Month -> Provider
    q = (
        db.query(Signup, Shift, Month, Provider)
        .join(Shift, Signup.shift_id == Shift.id)
        .join(Month, Shift.month_id == Month.id)
        .join(Provider, Signup.provider_id == Provider.id)
    )

    if month:
        try:
            year, m = map(int, month.split("-"))
        except ValueError:
            raise HTTPException(status_code=400, detail="month must be 'YYYY-MM'")
        q = q.filter(Month.year == year, Month.month == m)

    rows = q.order_by(Month.year, Month.month, Shift.date, Provider.name).all()

    results: List[AdminSignupOut] = []
    for su, sh, mo, pr in rows:
        results.append(
            AdminSignupOut(
                provider_id=pr.id,
                provider_name=pr.name,
                date=sh.date,
                month=f"{mo.year:04d}-{mo.month:02d}",
                desired_nights=su.desired_nights,
                locked=su.locked,
            )
        )
    return results
