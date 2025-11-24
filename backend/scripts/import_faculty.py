#!/usr/bin/env python3
"""
Import faculty from CSV file into the database.
Run this once to populate the faculty table.

Usage:
    python backend/scripts/import_faculty.py
"""

import csv
import sys
from pathlib import Path

# Add backend to path so we can import models
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Faculty, SessionLocal, engine, Base
from auth import hash_password  # Use the same hash_password from auth.py

DEFAULT_PASSWORD = "PCCM2025!"


def import_faculty_csv(csv_path: str):
    """Import faculty from CSV file"""
    db = SessionLocal()
    
    try:
        # Ensure tables exist
        print("[Import] Ensuring database tables exist...")
        Base.metadata.create_all(bind=engine)
        
        # Check if CSV exists
        if not Path(csv_path).exists():
            print(f"❌ Error: CSV file not found at {csv_path}")
            return
        
        imported = 0
        skipped = 0
        
        print(f"[Import] Reading faculty from {csv_path}...")
        print("-" * 80)
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                faculty_id = row['id'].strip()
                
                # Check if faculty already exists
                existing = db.query(Faculty).filter_by(id=faculty_id).first()
                if existing:
                    print(f"⏭️  Skipping {row['name']} - already exists")
                    skipped += 1
                    continue
                
                # Convert boolean strings to Python booleans
                active = row['active'].strip().upper() == 'TRUE'
                is_admin = row['is_admin'].strip().upper() == 'TRUE'
                
                # Create Faculty record with bcrypt-hashed password
                faculty = Faculty(
                    id=faculty_id,
                    name=row['name'].strip(),
                    email=row['email'].strip(),
                    rank=row['rank'].strip().lower(),  # Ensure lowercase
                    clinical_effort_pct=int(row['clinical_effort_pct']),
                    base_points=int(row['base_points']),
                    bonus_points=int(row['bonus_points']),
                    active=active,
                    is_admin=is_admin,
                    password_hash=hash_password(DEFAULT_PASSWORD),  # Now uses bcrypt
                    password_changed=False,  # All start with default password
                    registered=True  # All in CSV are considered registered
                )
                
                db.add(faculty)
                imported += 1
                
                admin_badge = " 🔑 ADMIN" if is_admin else ""
                print(f"✅ Imported: {faculty.name} ({faculty.email}){admin_badge}")
        
        # Commit all changes
        db.commit()
        
        print("-" * 80)
        print(f"\n🎉 Import complete!")
        print(f"   ✅ Imported: {imported} faculty members")
        print(f"   ⏭️  Skipped: {skipped} (already exist)")
        
        # Show admin users
        admins = db.query(Faculty).filter_by(is_admin=True).all()
        if admins:
            print(f"\n🔑 Admin users:")
            for admin in admins:
                print(f"   - {admin.name} ({admin.email})")
        
        print(f"\n🔐 Default password for all users: {DEFAULT_PASSWORD}")
        print("   Users will be prompted to change on first login.")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error importing faculty: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # Default CSV path
    csv_path = "faculty.csv"
    
    # Allow custom CSV path from command line
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    
    print("=" * 80)
    print("PCCM Faculty Import Script")
    print("=" * 80)
    print()
    
    import_faculty_csv(csv_path)
