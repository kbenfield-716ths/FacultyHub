# backend/app.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session

from .models import (
    SessionLocal, init_db,
    Provider, Month, Shift, Signup, Assignment
)
from .optimizer_bridge import run_optimizer_for_month
import csv
import os

app = FastAPI()

# Allow calls from your GitHub Pages site (you can tighten this later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later: ["https://kbenfield-716ths.github.io"]
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
# ---------- CSV Provider Seeding ----------

def seed_providers_from_csv(db: Session):
    """
    Reads faculty.csv at the project root and seeds Provider table.
    Expected columns: faculty_id, name, email
    """
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "faculty.csv")

    if not os.path.exists(csv_path):
        print(f"⚠️ faculty.csv not found at {csv_path}, skipping provider seeding.")
        return

    with open(csv_path, newline='', encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Detect header row
    has_header = False
    if rows and rows[0][0].lower().strip() == "faculty_id":
        has_header = True
        rows = rows[1:]

    for row in rows:
        if len(row) < 2:
            continue

        pid = row[0].strip()
        name = row[1].strip()

        existing = db.query(Provider).get(pid)
        if not existing:
            print(f"🌱 Seeding provider: {pid} -> {name}")
            db.add(Provider(id=pid, name=name))

    db.commit()

# ---------- Pydantic Schemas ----------

class SignupPayload(BaseModel):
    provider_id: str
    provider_name: str
    month: str            # "2025-11"
    desired_nights: int
    dates: List[date]     # ["2025-11-06", ...]
    locked_dates: List[date] = []


class SignupOut(BaseModel):
    provider_id: str
    provider_name: str
    date: date
    month: str
    desired_nights: int
    locked: bool

    class Config:
        orm_mode = True


class ProviderOut(BaseModel):
    id: str
    name: str

    class Config:
        orm_mode = True

@app.on_event("startup")
def startup_seed():
    db = SessionLocal()
    try:
        seed_providers_from_csv(db)
    finally:
        db.close()
        
# ---------- Signup endpoint ----------

@app.post("/api/signup")
def save_signup(payload: SignupPayload, db: Session = Depends(get_db)):
    # Ensure provider exists
    provider = db.query(Provider).get(payload.provider_id)
    if not provider:
        provider = Provider(id=payload.provider_id, name=payload.provider_name)
        db.add(provider)

    # Ensure Month row exists
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

    # Ensure shifts exist for the selected dates
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

    # Clear old signups for this provider in this month
    shift_ids = [s.id for s in existing_shifts.values()]
    db.query(Signup).filter(
        Signup.provider_id == payload.provider_id,
        Signup.shift_id.in_(shift_ids)
    ).delete(synchronize_session=False)

    # Write new signups
    locked_set = set(payload.locked_dates)
    for d in payload.dates:
        su = Signup(
            provider_id=payload.provider_id,
            provider_name=payload.provider_name,
            date=d,
            month=payload.month,
            desired_nights=payload.desired_nights,
            locked=d in locked_set,
            shift_id=existing_shifts[d].id,
        )
        db.add(su)

    db.commit()
    return {"status": "ok"}


# ---------- Admin: list signups ----------

@app.get("/api/admin/signups", response_model=List[SignupOut])
def list_signups(
    month: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Signup)
    if month:
        q = q.filter(Signup.month == month)
    return q.order_by(Signup.provider_name, Signup.date).all()


# ---------- Providers list (for dropdown) ----------

@app.get("/api/providers", response_model=List[ProviderOut])
def list_providers(db: Session = Depends(get_db)):
    providers = db.query(Provider).order_by(Provider.name).all()
    return providers
