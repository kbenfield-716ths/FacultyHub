# backend/models.py
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime,
    ForeignKey, create_engine, text
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import os

# Use persistent volume if available, fallback to local
db_path = "/data/moonlighter.db" if os.path.exists("/data") else "./moonlighter.db"
DATABASE_URL = f"sqlite:///{db_path}"

Base = declarative_base()
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# ==========================================
# MOONLIGHTING MODELS (Existing)
# ==========================================

class Provider(Base):
    """Faculty member for moonlighting shifts"""
    __tablename__ = "providers"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    email = Column(String, nullable=True)
    
    signups = relationship("Signup", back_populates="provider")
    assignments = relationship("Assignment", back_populates="provider")


class Month(Base):
    __tablename__ = "months"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    
    shifts = relationship("Shift", back_populates="month")


class Shift(Base):
    """Moonlighting night shifts"""
    __tablename__ = "shifts"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    month_id = Column(Integer, ForeignKey("months.id"), nullable=False)
    date = Column(Date, nullable=False)
    slots = Column(Integer, default=1)
    
    month = relationship("Month", back_populates="shifts")
    signups = relationship("Signup", back_populates="shift")
    assignments = relationship("Assignment", back_populates="shift")


class Signup(Base):
    """Faculty requests for moonlighting shifts"""
    __tablename__ = "signups"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    provider_id = Column(String, ForeignKey("providers.id"), nullable=False, index=True)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=False, index=True)
    desired_nights = Column(Integer, nullable=False)
    locked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    provider = relationship("Provider", back_populates="signups")
    shift = relationship("Shift", back_populates="signups")


class Assignment(Base):
    """Final moonlighting shift assignments"""
    __tablename__ = "assignments"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    provider_id = Column(String, ForeignKey("providers.id"), nullable=False)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    provider = relationship("Provider", back_populates="assignments")
    shift = relationship("Shift", back_populates="assignments")


# ==========================================
# FACULTY SCHEDULING MODELS (Service Availability)
# ==========================================

class Faculty(Base):
    """Faculty member with scheduling profile and authentication"""
    __tablename__ = "faculty"
    
    # Core identity (UVA computing ID: "KE4Z", "IN2C", etc.)
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False)
    
    # Authentication
    password_hash = Column(String)
    password_changed = Column(Boolean, default=False)
    registered = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # Scheduling profile
    rank = Column(String, nullable=False)  # assistant, associate, full
    clinical_effort_pct = Column(Integer, nullable=False)
    base_points = Column(Integer, nullable=False)
    bonus_points = Column(Integer, default=0)  # Earned from volunteering
    active = Column(Boolean, default=True)
    
    # Moonlighting participation
    moonlighter = Column(Boolean, default=False)  # Whether faculty does moonlighting shifts
    
    # Service week commitments (for inpatient scheduling)
    # These define how many weeks per year this faculty member is expected to work each service
    micu_weeks = Column(Integer, default=0)        # Number of MICU weeks per year
    app_icu_weeks = Column(Integer, default=0)     # Number of APP-ICU weeks per year  
    procedure_weeks = Column(Integer, default=0)   # Number of Procedure weeks per year
    consult_weeks = Column(Integer, default=0)     # Number of Consult weeks per year
    
    # Relationships
    unavailability_requests = relationship("UnavailabilityRequest", back_populates="faculty")
    service_assignments = relationship("ServiceWeekAssignment", back_populates="faculty")


class ServiceWeek(Base):
    """The 52 weeks of the academic year for service availability scheduling"""
    __tablename__ = "service_weeks"
    
    id = Column(String, primary_key=True, index=True)  # "W01-2026", "W02-2026", etc.
    week_number = Column(Integer, nullable=False)
    label = Column(String, nullable=False)  # "Week 1 (Jul 7)"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    year = Column(Integer, nullable=False)
    
    # Week characteristics
    week_type = Column(String, default="regular")  # regular, summer, spring_break, thanksgiving, christmas
    point_cost_off = Column(Integer, default=5)     # Cost to request unavailability
    point_reward_work = Column(Integer, default=0)  # Bonus for volunteering
    min_staff_required = Column(Integer, default=5)
    
    # Historic data seeding (for previous years before system was deployed)
    historic_unavailable_count = Column(Integer, default=0)  # Number of faculty unavailable (from seed data)
    
    # Relationships
    unavailability_requests = relationship("UnavailabilityRequest", back_populates="week")
    service_assignments = relationship("ServiceWeekAssignment", back_populates="week")


class UnavailabilityRequest(Base):
    """Faculty unavailability requests for specific weeks"""
    __tablename__ = "unavailability_requests"
    
    id = Column(String, primary_key=True, index=True)
    faculty_id = Column(String, ForeignKey('faculty.id'), nullable=False, index=True)
    week_id = Column(String, ForeignKey('service_weeks.id'), nullable=False, index=True)
    
    # Status: "unavailable" (requests time off), "available" (volunteers), "assigned" (final)
    status = Column(String, nullable=False, default="unavailable")
    
    # Points tracking
    points_spent = Column(Integer, default=0)   # For requesting unavailability
    points_earned = Column(Integer, default=0)  # For volunteering
    
    # Draft priority tracking
    gives_priority = Column(Boolean, default=False)  # Working holiday gives next year priority
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    faculty = relationship("Faculty", back_populates="unavailability_requests")
    week = relationship("ServiceWeek", back_populates="unavailability_requests")


class ServiceWeekAssignment(Base):
    """Actual service week assignments (MICU, APP-ICU, Procedures, Consults)"""
    __tablename__ = "service_week_assignments"
    
    id = Column(String, primary_key=True, index=True)
    faculty_id = Column(String, ForeignKey('faculty.id'), nullable=False, index=True)
    week_id = Column(String, ForeignKey('service_weeks.id'), nullable=False, index=True)
    
    # Service type: "MICU", "APP-ICU", "Procedures", "Consults"
    service_type = Column(String, nullable=False, index=True)
    
    # Import tracking
    imported = Column(Boolean, default=False)  # True if from historic CSV
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    faculty = relationship("Faculty", back_populates="service_assignments")
    week = relationship("ServiceWeek", back_populates="service_assignments")


# ==========================================
# DATABASE INITIALIZATION
# ==========================================

def init_db():
    """Initialize database with tables and optimizations"""
    print("[Database] Creating tables and indexes...")
    Base.metadata.create_all(bind=engine)
    
    # Database optimizations using text() for raw SQL
    try:
        with engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.execute(text("PRAGMA cache_size=-20000"))
            conn.execute(text("PRAGMA mmap_size=10485760"))
            conn.execute(text("PRAGMA synchronous=NORMAL"))
            
            # Add indexes for faculty scheduling tables
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_faculty_email ON faculty(email)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_faculty_active ON faculty(active)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_unavailability_requests_faculty_week 
                ON unavailability_requests(faculty_id, week_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_unavailability_requests_status 
                ON unavailability_requests(status)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_service_weeks_number 
                ON service_weeks(week_number)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_service_weeks_year 
                ON service_weeks(year)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_service_assignments_faculty_week 
                ON service_week_assignments(faculty_id, week_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_service_assignments_service_type 
                ON service_week_assignments(service_type)
            """))
            
            conn.execute(text("ANALYZE"))
            conn.commit()
        print("[Database] Initialization complete with optimizations")
    except Exception as e:
        print(f"[Database] Warning: Could not apply optimizations: {e}")
        print("[Database] Initialization complete (without optimizations)")


def get_db():
    """Dependency for FastAPI endpoints"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
