# backend/app.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from pathlib import Path
import csv
import io

from sqlalchemy.orm import Session

from .models import (
    SessionLocal, init_db,
    Provider, Month, Shift, Signup, Assignment
)
from .optimizer_bridge import run_optimizer_for_month

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

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

    # Log CSV headers so we know they match faculty_id,name,email
    with FACULTY_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        print(f"[seed_providers] CSV headers: {headers}")

    existing_count = db.query(Provider).count()
    print(f"[seed_providers] Existing providers in DB: {existing_count}")

    if existing_count > 0:
        print("[seed_providers] Providers already present, NOT reseeding.")
        return

    # Re-open to actually read rows
    inserted = 0
    with FACULTY_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            faculty_id = (row.get("faculty_id") or "").strip()
            name = (row.get("name") or "").strip()
            email = (row.get("email") or "").strip()

            # Log each row briefly
            print(f"[seed_providers] Row {idx}: faculty_id='{faculty_id}', name='{name}', email='{email}'")

            # Skip incomplete rows
            if not faculty_id or not name:
                print(f"[seed_providers]  -> skipping row {idx}, missing id or name")
                continue

            # Avoid duplicates in CSV
            exists = db.query(Provider).filter(Provider.id == faculty_id).first()
            if exists:
                print(f"[seed_providers]  -> row {idx} duplicate faculty_id {faculty_id}, skipping")
                continue

            db.add(Provider(id=faculty_id, name=name, email=email or None))
            inserted += 1

    db.commit()
    print(f"[seed_providers] Seeding complete. Inserted {inserted} providers.")

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
    q = db.query(Signup).join(Signup.shift).join(Shift.month).join(Signup.provider)

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
                month=f"{s.shift.month.year:04d}-{s.shift.month.month:02d}",
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

# ---------- Admin: list signups ----------

class SignupOut(BaseModel):
    provider_id: str
    provider_name: str
    date: date
    month: str
    desired_nights: int
    locked: bool

    class Config:
        from_attributes = True


@app.get("/api/admin/signups", response_model=List[SignupOut])
def list_signups(
    month: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Return one row per provider-date signup:
    - provider_id, provider_name
    - date
    - month (YYYY-MM)
    - desired_nights
    - locked
    """
    q = (
        db.query(
            Signup.provider_id,
            Provider.name.label("provider_name"),
            Shift.date.label("date"),
            Month.year.label("year"),
            Month.month.label("month_num"),
            Signup.desired_nights,
            Signup.locked,
        )
        .join(Provider, Signup.provider_id == Provider.id)
        .join(Shift, Signup.shift_id == Shift.id)
        .join(Month, Shift.month_id == Month.id)
    )

    if month:
        year, mnum = map(int, month.split("-"))
        q = q.filter(Month.year == year, Month.month == mnum)

    rows = q.order_by(Provider.name, Shift.date).all()

    result: List[SignupOut] = []
    for r in rows:
        month_str = f"{r.year:04d}-{r.month_num:02d}"
        result.append(
            SignupOut(
                provider_id=r.provider_id,
                provider_name=r.provider_name,
                date=r.date,
                month=month_str,
                desired_nights=r.desired_nights,
                locked=bool(r.locked),
            )
        )
    return result


# ---------- Admin: run optimizer for a month ----------

@app.post("/api/admin/run_optimizer")
def run_optimizer_endpoint(
    month: str,
    db: Session = Depends(get_db),
):
    """
    Run the scheduling optimizer for a given month ("YYYY-MM").
    """
    # If run_optimizer_for_month isn't fully implemented yet,
    # you can temporarily stub it out to just return [].
    assignments = run_optimizer_for_month(month, db)
    if assignments is None:
        count = 0
    else:
        try:
            count = len(assignments)
        except TypeError:
            count = 0

    return {"status": "ok", "month": month, "assigned_shifts": count}


# ---------- Admin: CSV export of signups ----------

@app.get("/api/admin/signups_csv", response_class=PlainTextResponse)
def signups_csv(
    month: str,
    db: Session = Depends(get_db),
):
    """
    Export all signups for a given month as CSV:
    provider_id,provider_name,date,month,desired_nights,locked
    """
    year, mnum = map(int, month.split("-"))

    q = (
        db.query(
            Signup.provider_id,
            Provider.name.label("provider_name"),
            Shift.date.label("date"),
            Month.year.label("year"),
            Month.month.label("month_num"),
            Signup.desired_nights,
            Signup.locked,
        )
        .join(Provider, Signup.provider_id == Provider.id)
        .join(Shift, Signup.shift_id == Shift.id)
        .join(Month, Shift.month_id == Month.id)
        .filter(Month.year == year, Month.month == mnum)
        .order_by(Provider.name, Shift.date)
    )

    rows = q.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["provider_id", "provider_name", "date", "month", "desired_nights", "locked"])

    for r in rows:
        month_str = f"{r.year:04d}-{r.month_num:02d}"
        writer.writerow([
            r.provider_id,
            r.provider_name,
            r.date.isoformat(),
            month_str,
            r.desired_nights,
            int(bool(r.locked)),
        ])

    csv_text = output.getvalue()
    headers = {
        "Content-Disposition": f'attachment; filename="signups_{month}.csv"'
    }
    return PlainTextResponse(csv_text, headers=headers)
