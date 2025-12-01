#!/usr/bin/env python3
"""
Seed historic unavailability data for past academic years.

This script loads CSV files from backend/seed_data/ and populates the
historic_unavailable_count field in VacationWeek for past years.

Run this manually or as part of initial setup.
"""

import csv
import sys
from pathlib import Path
from sqlalchemy.orm import Session

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from models import SessionLocal, VacationWeek


def seed_unavailability_for_year(db: Session, year: int, csv_path: Path) -> dict:
    """
    Seed historic unavailability data for a specific year.
    
    Args:
        db: Database session
        year: Academic year (e.g., 2025 for 2025-2026)
        csv_path: Path to CSV file with format: week_number,unavailable_count
    
    Returns:
        Dict with seeding results
    """
    
    if not csv_path.exists():
        return {"success": False, "error": f"CSV file not found: {csv_path}"}
    
    # Check if weeks exist for this year
    weeks = db.query(VacationWeek).filter(VacationWeek.year == year).all()
    if not weeks:
        return {
            "success": False,
            "error": f"No weeks found for year {year}. Generate weeks first."
        }
    
    # Create a lookup dict for weeks
    weeks_by_number = {w.week_number: w for w in weeks}
    
    # Load CSV data
    updates = 0
    errors = []
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        
        if 'week_number' not in reader.fieldnames or 'unavailable_count' not in reader.fieldnames:
            return {
                "success": False,
                "error": "CSV must have columns: week_number,unavailable_count"
            }
        
        for row_num, row in enumerate(reader, start=2):
            try:
                week_number = int(row['week_number'])
                unavailable_count = int(row['unavailable_count'])
                
                if week_number < 1 or week_number > 52:
                    errors.append(f"Row {row_num}: Invalid week number {week_number}")
                    continue
                
                if week_number not in weeks_by_number:
                    errors.append(f"Row {row_num}: Week {week_number} not found in database")
                    continue
                
                week = weeks_by_number[week_number]
                week.historic_unavailable_count = unavailable_count
                updates += 1
                
            except ValueError as e:
                errors.append(f"Row {row_num}: {str(e)}")
                continue
    
    db.commit()
    
    return {
        "success": True,
        "year": year,
        "updates": updates,
        "errors": errors if errors else None
    }


def seed_all_historic_data():
    """
    Seed all historic unavailability data from CSV files in seed_data/
    """
    
    seed_data_dir = Path(__file__).parent / "seed_data"
    
    if not seed_data_dir.exists():
        print(f"[Seeding] No seed_data directory found at {seed_data_dir}")
        return
    
    # Look for CSV files matching pattern: unavailability_YYYY_YY.csv
    csv_files = list(seed_data_dir.glob("unavailability_*.csv"))
    
    if not csv_files:
        print("[Seeding] No unavailability CSV files found in seed_data/")
        return
    
    print(f"[Seeding] Found {len(csv_files)} unavailability seed files")
    
    db = SessionLocal()
    try:
        for csv_file in csv_files:
            # Extract year from filename: unavailability_2025_26.csv -> 2025
            try:
                year = int(csv_file.stem.split('_')[1])
            except (IndexError, ValueError):
                print(f"[Seeding] Skipping {csv_file.name}: Invalid filename format")
                continue
            
            print(f"[Seeding] Processing {csv_file.name} for year {year}...")
            result = seed_unavailability_for_year(db, year, csv_file)
            
            if result["success"]:
                print(f"[Seeding] ✓ Updated {result['updates']} weeks for {year}")
                if result.get("errors"):
                    print(f"[Seeding]   Warnings: {len(result['errors'])} rows had issues")
            else:
                print(f"[Seeding] ✗ Failed for {year}: {result['error']}")
    
    finally:
        db.close()


if __name__ == "__main__":
    print("[Seeding] Starting historic unavailability data seeding...")
    seed_all_historic_data()
    print("[Seeding] Complete!")
