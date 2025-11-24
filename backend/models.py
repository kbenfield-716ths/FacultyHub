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
    assignments = relationship("Assignment", back_populates="assignments")


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
# FACULTY SCHEDULING MODELS (New)
# ==========================================

class Faculty(Base):
    """Faculty member with scheduling profile and authentication"""
    __tablename__ = "faculty"
    
    # Core identity (uses same ID as Provider for seamless integration)
    id = Column(String, primary_key=True, index=True)
    faculty_id = Column(String, unique=True, index=True)  # Display ID like "F001"
    name = Column(String, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False)
    
    # Authentication
    password_hash = Column(String)
    password_changed = Column(Boolean, default=False)
    registered = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    
    # Scheduling profile
    rank = Column(String, nullable=False)  # assistant, associate, full
    clinical_effort_pct = Column(Integer, nullable=False)
    base_points = Column(Integer, nullable=False)
    active = Column(Boolean, default=True)
    
    # Relationships
    availabilities = relationship("Availability", back_populates="faculty")


class Week(Base):
    """The 52 weeks of the academic year"""
    __tablename__ = "weeks"
    
    id = Column(String, primary_key=True, index=True)  # e.g., "W01", "W02"
    week_number = Column(Integer, nullable=False, unique=True)
    label = Column(String, nullable=False)  # e.g., "Week 1 (Jul 7)"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    # Week characteristics
    week_type = Column(String, default="regular")  # regular, summer, spring_break, thanksgiving, christmas
    point_cost_off = Column(Integer, default=5)     # Cost to take week off
    point_reward_work = Column(Integer, default=0)  # Bonus for volunteering
    min_staff_required = Column(Integer, default=5)
    
    # Relationships
    availabilities = relationship("Availability", back_populates="week")


class Availability(Base):
    """Faculty availability for vacation weeks"""
    __tablename__ = "availabilities"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    faculty_id = Column(String, ForeignKey("faculty.id"), nullable=False, index=True)
    week_id = Column(String, ForeignKey("weeks.id"), nullable=False, index=True)
    
    # Status: "unavailable" (wants off), "available" (volunteers), "assigned" (final)
    status = Column(String, nullable=False, default="unavailable")
    
    # Points tracking
    points_spent = Column(Integer, default=0)   # For taking week off
    points_earned = Column(Integer, default=0)  # For volunteering
    
    # Draft priority tracking
    gives_priority = Column(Boolean, default=False)  # Working holiday gives next year priority
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    faculty = relationship("Faculty", back_populates="availabilities")
    week = relationship("Week", back_populates="availabilities")


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
            
            # Add indexes for new faculty scheduling tables
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_faculty_email ON faculty(email)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_faculty_active ON faculty(active)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_availabilities_faculty_week 
                ON availabilities(faculty_id, week_id)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_availabilities_status 
                ON availabilities(status)
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_weeks_number ON weeks(week_number)
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
