#!/usr/bin/env python3
"""
Rehash all passwords in the database from SHA256 to bcrypt.
Run this once to fix the password hashing mismatch.

Usage:
    python backend/scripts/rehash_passwords.py
"""

import sys
from pathlib import Path

# Add backend to path so we can import models
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Faculty, SessionLocal
from auth import hash_password

DEFAULT_PASSWORD = "PCCM2025!"


def rehash_all_passwords():
    """Rehash all faculty passwords to use bcrypt"""
    db = SessionLocal()
    
    try:
        # Get all faculty
        all_faculty = db.query(Faculty).all()
        
        if not all_faculty:
            print("❌ No faculty found in database")
            return
        
        print("=" * 80)
        print("Password Rehashing Script")
        print("=" * 80)
        print(f"\nFound {len(all_faculty)} faculty members")
        print(f"Will rehash all passwords to: {DEFAULT_PASSWORD}")
        print("-" * 80)
        
        updated = 0
        
        for faculty in all_faculty:
            # Rehash password using bcrypt
            faculty.password_hash = hash_password(DEFAULT_PASSWORD)
            faculty.password_changed = False
            updated += 1
            print(f"✅ Rehashed password for: {faculty.name} ({faculty.id})")
        
        # Commit changes
        db.commit()
        
        print("-" * 80)
        print(f"\n🎉 Rehashing complete!")
        print(f"   ✅ Updated: {updated} passwords")
        print(f"\n🔐 All passwords reset to: {DEFAULT_PASSWORD}")
        print("   Users will be prompted to change on first login.")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error rehashing passwords: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("\n⚠️  WARNING: This will reset ALL passwords to the default!")
    response = input("Continue? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        rehash_all_passwords()
    else:
        print("❌ Cancelled")
