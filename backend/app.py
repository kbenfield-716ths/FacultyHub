# backend/app.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from pathlib import Path
import csv

from sqlalchemy.orm import Session

from .models import (
    SessionLocal, init_db,
    Provider, Month, Shift, Signup, Assignment
)
from .optimizer_bridge import run_optimizer_for_month

app = FastAPI()

# Allow calls from your GitHub Pages site (you can tighten this later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later: ["https://kbenfield-716ths.github.io"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- DB session dependency ----------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
        from_attributes = True  # pydantic v2 replacement for orm_mode


class ProviderOut(BaseModel):
    id: str
    name: str
    email: Optional[str] = None

    class Config:
        from_attributes = True


# ---------- Provider seeding from CSV ----------

# In the container, app.py will live at /app/backend/app.py
# faculty.csv is copied to /app/faculty.csv by the Dockerfile.
DATA_DIR = Path(__file__).resolve().parent.parent  # /app
FACULTY_CSV = DATA_DIR / "faculty.csv"


def seed_providers_from_csv(db: Session) -> None:
    """Populate Provider table from faculty.csv if it's empty."""
    print(f"[seed_providers] Looking for CSV at {FACULTY_CSV}")
    if not FACULTY_CSV.exists():
        print("[seed_providers] faculty.csv not found, skipping.")
        return

    existing_count = db.query(Provider).count()
    if existing_count > 0:
        print(f"[seed_providers] Providers already exist ({existing_count}), skipping.")
        return

    print(f"[seed_providers] Loading providers from {FACULTY_CSV}")
    with FACULTY_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            faculty_id = row.get("faculty_id", "").strip()
            name = row.get("name", "").strip()
            email = row.get("email", "").strip()

            if not faculty_id or not name:
                continue

            # Avoid duplicates in CSV
            exists = db.query(Provider).filter(Provider.id == faculty_id).first()
            if exists:
                continue

            db.add(Provider(id=faculty_id, name=name, email=email or None))

    db.commit()
    print("[seed_providers] Done seeding providers from CSV")


# ---------- FastAPI lifecycle ----------

@app.on_event("startup")
def startup_event():
    # make sure tables exist
    init_db()
    # seed providers from CSV if needed
    db = SessionLocal()
    try:
        seed_providers_from_csv(db)
    finally:
        db.close()


# ---------- Signup endpoint ----------

@app.post("/api/signup")
def save_signup(payload: SignupPayload, db: Session = Depends(get_db)):
    # Ensure provider exists (or update name/email if needed)
    provider = db.query(Provider).get(payload.provider_id)
    if not provider:
        provider = Provider(id=payload.provider_id, name=payload.provider_name)
        db.add(provider)
    else:
        # keep name in sync with whatever comes from the front-end
        provider.name = payload.provider_name

    # Ensure Month row exists
    year, month_num = map(int, payload.month.split("-"))
    month_row = (
        db.query(Month)
        .filter(Month.year == year, Month.month == month_num)
        .first()
    )
    if not month_row:
        month_row = Month(year=year, month=month_num)
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
    q = db.query(Signup).join(Signup.shift).join(Shift.month_rel).join(Signup.provider)

    if month:
        year, mnum = map(int, month.split("-"))
        q = q.filter(Month.year == year, Month.month == mnum)

    signups = q.order_by(Provider.name, Shift.date).all()

    # Manually shape into SignupOut
    result: List[SignupOut] = []
    for s in signups:
        result.append(
            SignupOut(
                provider_id=s.provider_id,
                provider_name=s.provider.name if s.provider else "",
                date=s.shift.date,
                month=f"{s.shift.month_rel.year:04d}-{s.shift.month_rel.month:02d}",
                desired_nights=s.desired_nights,
                locked=s.locked,
            )
        )
    return result


# ---------- Providers list (for dropdown) ----------

@app.get("/api/providers", response_model=List[ProviderOut])
def list_providers(db: Session = Depends(get_db)):
    providers = db.query(Provider).order_by(Provider.name).all()
    return providers
