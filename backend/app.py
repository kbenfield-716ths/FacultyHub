# backend/app.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles
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
from .notion_integration import get_notion_kb
from fastapi.middleware.gzip import GZipMiddleware
from .routes.admin_faculty import router as admin_faculty_router
from .routes.admin_service import router as admin_service_router
from .routes.auth import router as auth_router

app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include routers FIRST - before catch-all routes
app.include_router(auth_router)
app.include_router(admin_faculty_router)
app.include_router(admin_service_router)

# Serve static files (HTML, CSS, JS, icons, manifest)
# HTML files are in the parent directory of backend/
STATIC_DIR = Path(__file__).resolve().parent.parent  # Go up to root directory
BACKEND_STATIC_DIR = Path(__file__).resolve().parent / "static"

# Mount icons if they exist
if (STATIC_DIR / "icons").exists():
    app.mount("/icons", StaticFiles(directory=str(STATIC_DIR / "icons")), name="icons")

# Allow calls from anywhere (since we're serving the frontend too now)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
        from_attributes = True


class ProviderOut(BaseModel):
    id: str
    name: str
    email: Optional[str] = None

    class Config:
        from_attributes = True


class ProviderCreate(BaseModel):
    id: str
    name: str
    email: Optional[str] = None


class ProviderUpdate(BaseModel):
    name: str
    email: Optional[str] = None


class AssignmentOut(BaseModel):
    provider_id: str
    provider_name: str
    date: date
    month: str

    class Config:
        from_attributes = True

# ---------- FastAPI lifecycle ----------

@app.on_event("startup")
def startup_event():
    # make sure tables exist
    init_db()
    
    # Create default admin user if none exists
    from .models import Faculty, SessionLocal
    from .auth import hash_password
    
    db = SessionLocal()
    try:
        admin_count = db.query(Faculty).filter_by(is_admin=True).count()
        if admin_count == 0:
            # Create default admin
            admin = Faculty(
                id="ADMIN",
                name="Administrator",
                email="admin@example.com",
                rank="full",
                clinical_effort_pct=0,
                base_points=0,
                is_admin=True,
                password_hash=hash_password("PCCM2025!"),
                password_changed=False,
                registered=True,
                active=True
            )
            db.add(admin)
            db.commit()
            print("[Startup] Created default admin user: ADMIN / PCCM2025!")
    except Exception as e:
        print(f"[Startup] Error creating admin user: {e}")
    finally:
        db.close()


# ========================================
# API ROUTES - MUST COME BEFORE STATIC FILE ROUTES
# ========================================

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


# ---------- Admin: list assignments (generated schedule) ----------

@app.get("/api/admin/assignments", response_model=List[AssignmentOut])
def list_assignments(
    month: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Return the generated schedule (assignments) for a month.
    """
    q = (
        db.query(
            Assignment.provider_id,
            Provider.name.label("provider_name"),
            Shift.date.label("date"),
            Month.year.label("year"),
            Month.month.label("month_num"),
        )
        .join(Provider, Assignment.provider_id == Provider.id)
        .join(Shift, Assignment.shift_id == Shift.id)
        .join(Month, Shift.month_id == Month.id)
    )

    if month:
        year, mnum = map(int, month.split("-"))
        q = q.filter(Month.year == year, Month.month == mnum)

    rows = q.order_by(Shift.date, Provider.name).all()

    result: List[AssignmentOut] = []
    for r in rows:
        month_str = f"{r.year:04d}-{r.month_num:02d}"
        result.append(
            AssignmentOut(
                provider_id=r.provider_id,
                provider_name=r.provider_name,
                date=r.date,
                month=month_str,
            )
        )
    return result


# ---------- Providers list (for dropdown) ----------

@app.get("/api/providers", response_model=List[ProviderOut])
def list_providers(db: Session = Depends(get_db)):
    """Get all providers for moonlighting system."""
    providers = db.query(Provider).order_by(Provider.name).all()
    return providers


# ---------- Admin: Provider management ----------

@app.post("/api/admin/providers")
def create_provider(provider: ProviderCreate, db: Session = Depends(get_db)):
    """
    Add a new provider.
    """
    existing = db.query(Provider).filter(Provider.id == provider.id).first()
    if existing:
        raise HTTPException(400, f"Provider with id '{provider.id}' already exists")
    
    new_provider = Provider(
        id=provider.id,
        name=provider.name,
        email=provider.email
    )
    db.add(new_provider)
    db.commit()
    db.refresh(new_provider)
    
    return {"status": "ok", "provider": {
        "id": new_provider.id,
        "name": new_provider.name,
        "email": new_provider.email
    }}


@app.put("/api/admin/providers/{provider_id}")
def update_provider(provider_id: str, provider: ProviderUpdate, db: Session = Depends(get_db)):
    """
    Update an existing provider's name and/or email.
    Provider ID cannot be changed.
    """
    existing = db.query(Provider).filter(Provider.id == provider_id).first()
    if not existing:
        raise HTTPException(404, f"Provider '{provider_id}' not found")
    
    # Update fields
    existing.name = provider.name
    existing.email = provider.email
    
    db.commit()
    db.refresh(existing)
    
    return {"status": "ok", "provider": {
        "id": existing.id,
        "name": existing.name,
        "email": existing.email
    }}


@app.delete("/api/admin/providers/{provider_id}")
def delete_provider(provider_id: str, db: Session = Depends(get_db)):
    """
    Delete a provider and all their signups/assignments.
    """
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(404, f"Provider '{provider_id}' not found")
    
    # Delete related signups and assignments
    db.query(Signup).filter(Signup.provider_id == provider_id).delete()
    db.query(Assignment).filter(Assignment.provider_id == provider_id).delete()
    
    # Delete provider
    db.delete(provider)
    db.commit()
    
    return {"status": "ok", "message": f"Provider '{provider.name}' deleted"}


# ---------- Admin: Clear data ----------

@app.delete("/api/admin/clear_month")
def clear_month_data(month: str, db: Session = Depends(get_db)):
    """
    Clear all signups and assignments for a specific month.
    Does not delete providers.
    """
    year, month_num = map(int, month.split("-"))
    month_row = (
        db.query(Month)
        .filter(Month.year == year, Month.month == month_num)
        .first()
    )
    
    if not month_row:
        return {"status": "ok", "message": "No data found for this month"}
    
    shift_ids = [s.id for s in month_row.shifts]
    
    # Delete assignments
    assignment_count = db.query(Assignment).filter(Assignment.shift_id.in_(shift_ids)).delete(synchronize_session=False)
    
    # Delete signups
    signup_count = db.query(Signup).filter(Signup.shift_id.in_(shift_ids)).delete(synchronize_session=False)
    
    # Delete shifts
    db.query(Shift).filter(Shift.month_id == month_row.id).delete(synchronize_session=False)
    
    # Delete month
    db.delete(month_row)
    db.commit()
    
    return {
        "status": "ok",
        "message": f"Cleared {signup_count} signups and {assignment_count} assignments for {month}"
    }


@app.delete("/api/admin/clear_all")
def clear_all_data(confirm: str, db: Session = Depends(get_db)):
    """
    Clear ALL data (signups, assignments, shifts, months).
    Does not delete providers.
    Requires confirmation string.
    """
    if confirm != "DELETE_ALL_DATA":
        raise HTTPException(400, "Confirmation string required: DELETE_ALL_DATA")
    
    assignment_count = db.query(Assignment).count()
    signup_count = db.query(Signup).count()
    shift_count = db.query(Shift).count()
    month_count = db.query(Month).count()
    
    db.query(Assignment).delete()
    db.query(Signup).delete()
    db.query(Shift).delete()
    db.query(Month).delete()
    db.commit()
    
    return {
        "status": "ok",
        "message": f"Cleared all data: {assignment_count} assignments, {signup_count} signups, {shift_count} shifts, {month_count} months"
    }


# ---------- Admin: run optimizer for a month ----------

@app.post("/api/admin/run_optimizer")
def run_optimizer_endpoint(
    month: str,
    strategy: str = "balanced",
    night_slots: int = 1,
    db: Session = Depends(get_db),
):
    """
    Run the scheduling optimizer for a given month ("YYYY-MM").
    """
    try:
        year, month_num = map(int, month.split("-"))
        month_row = (
            db.query(Month)
            .filter(Month.year == year, Month.month == month_num)
            .first()
        )
        
        if not month_row:
            raise HTTPException(404, f"No signups found for month {month}")
        
        # Run optimizer
        assignments = run_optimizer_for_month(db, month_row, strategy, night_slots)
        
        # Clear existing assignments for this month
        shift_ids = [s.id for s in month_row.shifts]
        db.query(Assignment).filter(Assignment.shift_id.in_(shift_ids)).delete(synchronize_session=False)
        
        # Save new assignments
        for provider, shift in assignments:
            assignment = Assignment(provider_id=provider.id, shift_id=shift.id)
            db.add(assignment)
        
        db.commit()
        
        return {
            "status": "ok",
            "month": month,
            "assigned_shifts": len(assignments),
            "strategy": strategy
        }
    except Exception as e:
        print(f"Optimizer error: {e}")
        raise HTTPException(500, f"Optimizer failed: {str(e)}")


# ---------- Admin: CSV export of signups ----------

@app.get("/api/admin/signups_csv", response_class=PlainTextResponse)
def signups_csv(
    month: str,
    db: Session = Depends(get_db),
):
    """
    Export all signups for a given month as CSV in optimizer format:
    faculty_id,name,desired_nights,requested_dates,priority
    """
    year, mnum = map(int, month.split("-"))

    # Get all signups for this month grouped by provider
    q = (
        db.query(
            Signup.provider_id,
            Provider.name,
            Shift.date,
            Signup.desired_nights,
        )
        .join(Provider, Signup.provider_id == Provider.id)
        .join(Shift, Signup.shift_id == Shift.id)
        .join(Month, Shift.month_id == Month.id)
        .filter(Month.year == year, Month.month == mnum)
        .order_by(Provider.name, Shift.date)
    )

    rows = q.all()
    
    # Group by provider
    from collections import defaultdict
    providers_data = defaultdict(lambda: {"dates": [], "desired_nights": 0, "name": ""})
    
    for r in rows:
        providers_data[r.provider_id]["name"] = r.name
        providers_data[r.provider_id]["dates"].append(r.date.isoformat())
        providers_data[r.provider_id]["desired_nights"] = r.desired_nights

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["faculty_id", "name", "desired_nights", "requested_dates", "priority"])

    for faculty_id, data in sorted(providers_data.items()):
        dates_str = ",".join(data["dates"])
        writer.writerow([
            faculty_id,
            data["name"],
            data["desired_nights"],
            dates_str,
            2  # Default priority
        ])

    csv_text = output.getvalue()
    headers = {
        "Content-Disposition": f'attachment; filename="moonlighter_template_{month}.csv"'
    }
    return PlainTextResponse(csv_text, headers=headers)

# Notion

@app.get("/api/knowledge-base")
def get_knowledge_base():
    """
    Get all articles from the knowledge base (Notion integration)
    """
    notion_kb = get_notion_kb()
    return notion_kb.get_all_articles()


@app.get("/api/knowledge-base/article/{article_id}")
def get_article(article_id: str):
    """
    Get a specific article with full content
    """
    notion_kb = get_notion_kb()
    article = notion_kb.get_article_by_id(article_id)
    
    if not article:
        raise HTTPException(404, "Article not found")
    
    return article


@app.get("/api/knowledge-base/search")
def search_knowledge_base(q: str):
    """
    Search articles by query
    """
    notion_kb = get_notion_kb()
    articles = notion_kb.search_articles(q)
    return {"articles": articles}


# ========================================
# STATIC FILE ROUTES - MUST COME AFTER API ROUTES
# ========================================

@app.get("/")
async def serve_index():
    """Serve the main index.html"""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"status": "ok", "message": "API running"}

@app.get("/favicon.ico")
async def serve_favicon_ico():
    favicon_path = STATIC_DIR / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(favicon_path)
    # Fallback to SVG
    svg_path = STATIC_DIR / "favicon.svg"
    if svg_path.exists():
        return FileResponse(svg_path, media_type="image/svg+xml")
    return {"error": "favicon not found"}

@app.get("/favicon.svg")
async def serve_favicon_svg():
    favicon_path = STATIC_DIR / "favicon.svg"
    if favicon_path.exists():
        response = FileResponse(favicon_path, media_type="image/svg+xml")
        response.headers["Cache-Control"] = "public, max-age=86400"
        return response 
    return {"error": "favicon.svg not found"}

@app.get("/manifest.json")
async def serve_manifest():
    manifest_path = STATIC_DIR / "manifest.json"
    if manifest_path.exists():
        response = FileResponse(manifest_path)
        response.headers["Cache-Control"] = "public, max-age=3600"
        return response
    return {"error": "manifest.json not found"}

@app.get("/service-worker.js")
async def serve_service_worker():
    """Serve the service worker file"""
    sw_path = STATIC_DIR / "service-worker.js"
    if sw_path.exists():
        response = FileResponse(sw_path, media_type="application/javascript")
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Service-Worker-Allowed"] = "/"
        return response
    return {"error": "service-worker.js not found"}

@app.get("/Service_Worker.js")
async def serve_service_worker_legacy():
    """Legacy route"""
    sw_path = STATIC_DIR / "service-worker.js"
    if sw_path.exists():
        response = FileResponse(sw_path, media_type="application/javascript")
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Service-Worker-Allowed"] = "/"
        return response
    old_sw_path = STATIC_DIR / "Service_Worker.js"
    if old_sw_path.exists():
        response = FileResponse(old_sw_path, media_type="application/javascript")
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Service-Worker-Allowed"] = "/"
        return response
    return {"error": "Service worker not found"}

@app.get("/{filename}.html")
async def serve_html_file(filename: str):
    """Serve any HTML file from root directory"""
    # Try exact match first
    html_path = STATIC_DIR / f"{filename}.html"
    if html_path.exists():
        response = FileResponse(html_path)
        response.headers["Cache-Control"] = "public, max-age=3600"
        return response
    
    # Try case-insensitive search
    for file in STATIC_DIR.glob("*.html"):
        if file.stem.lower() == filename.lower():
            response = FileResponse(file)
            response.headers["Cache-Control"] = "public, max-age=3600"
            return response
    
    for file in STATIC_DIR.glob("*.Html"):
        if file.stem.lower() == filename.lower():
            response = FileResponse(file)
            response.headers["Cache-Control"] = "public, max-age=3600"
            return response
    
    # Also try backend/static directory
    backend_html_path = BACKEND_STATIC_DIR / f"{filename}.html"
    if backend_html_path.exists():
        response = FileResponse(backend_html_path)
        response.headers["Cache-Control"] = "public, max-age=3600"
        return response
    
    return {"error": f"{filename}.html not found"}

@app.get("/style.css")
async def serve_style():
    css_path = STATIC_DIR / "style.css"
    if css_path.exists():
        response = FileResponse(css_path)
        response.headers["Cache-Control"] = "public, max-age=3600"
        return response
    return {"error": "style.css not found"}

@app.get("/cache-manager.js")
async def serve_cache_manager():
    cache_path = STATIC_DIR / "cache-manager.js"
    if cache_path.exists():
        response = FileResponse(cache_path, media_type="application/javascript")
        response.headers["Cache-Control"] = "public, max-age=3600"
        return response
    return {"error": "cache-manager.js not found"}

@app.get("/static/{path:path}")
async def serve_static(path: str):
    """Serve any static file from backend/static"""
    static_path = BACKEND_STATIC_DIR / path
    if static_path.exists() and static_path.is_file():
        return FileResponse(static_path)
    return {"error": f"Static file {path} not found"}

# Catch-all route for paths without extensions (e.g., /dashboard)
# THIS MUST BE LAST!
@app.get("/{path:path}")
async def serve_catch_all(path: str):
    """Catch-all for paths without extensions - try adding .html"""
    # Skip API routes - they should have been handled above
    if path.startswith("api/"):
        raise HTTPException(404, "API endpoint not found")
    
    # Try as .html file
    html_path = STATIC_DIR / f"{path}.html"
    if html_path.exists():
        response = FileResponse(html_path)
        response.headers["Cache-Control"] = "public, max-age=3600"
        return response
    
    # Try in backend/static
    backend_html_path = BACKEND_STATIC_DIR / f"{path}.html"
    if backend_html_path.exists():
        response = FileResponse(backend_html_path)
        response.headers["Cache-Control"] = "public, max-age=3600"
        return response
    
    raise HTTPException(404, f"Page not found: {path}")
