# backend/models.py
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime,
    ForeignKey, create_engine
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = "sqlite:///./moonlighter.db"

Base = declarative_base()
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Provider(Base):
    __tablename__ = "providers"

    id = Column(String, primary_key=True, index=True)  # e.g. email or slug
    name = Column(String, nullable=False)
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
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    month_id = Column(Integer, ForeignKey("months.id"), nullable=False)
    date = Column(Date, nullable=False)
    slots = Column(Integer, default=1)

    month = relationship("Month", back_populates="shifts")
    signups = relationship("Signup", back_populates="shift")
    assignments = relationship("Assignment", back_populates="shift")


class Signup(Base):
    __tablename__ = "signups"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    provider_id = Column(String, ForeignKey("providers.id"), nullable=False)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=False)
    desired_nights = Column(Integer, nullable=False)
    locked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    provider = relationship("Provider", back_populates="signups")
    shift = relationship("Shift", back_populates="signups")


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    provider_id = Column(String, ForeignKey("providers.id"), nullable=False)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    provider = relationship("Provider", back_populates="assignments")
    shift = relationship("Shift", back_populates="assignments")


def init_db():
    Base.metadata.create_all(bind=engine)
