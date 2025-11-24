#!/usr/bin/env python3
"""
Standalone script to rehash all passwords in the database.
This version doesn't use module imports.

Usage:
    python3 rehash_standalone.py
"""

import sqlite3
from passlib.context import CryptContext

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEFAULT_PASSWORD = "PCCM2025!"
DATABASE_PATH = "moonlighter.db"  # Adjust if your database is elsewhere


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def rehash_all_passwords():
    """Rehash all faculty passwords to use bcrypt"""
    
    try:
        # Connect to database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get all faculty
        cursor.execute("SELECT id, name FROM faculty")
        all_faculty = cursor.fetchall()
        
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
        new_hash = hash_password(DEFAULT_PASSWORD)
        
        for faculty_id, faculty_name in all_faculty:
            # Update password hash
            cursor.execute(
                "UPDATE faculty SET password_hash = ?, password_changed = 0 WHERE id = ?",
                (new_hash, faculty_id)
            )
            updated += 1
            print(f"✅ Rehashed password for: {faculty_name} ({faculty_id})")
        
        # Commit changes
        conn.commit()
        
        print("-" * 80)
        print(f"\n🎉 Rehashing complete!")
        print(f"   ✅ Updated: {updated} passwords")
        print(f"\n🔐 All passwords reset to: {DEFAULT_PASSWORD}")
        print("   Users will be prompted to change on first login.")
        
    except sqlite3.Error as e:
        print(f"\n❌ Database error: {e}")
        raise
    except Exception as e:
        print(f"\n❌ Error rehashing passwords: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    print("\n⚠️  WARNING: This will reset ALL passwords to the default!")
    print(f"Database: {DATABASE_PATH}")
    response = input("Continue? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        rehash_all_passwords()
    else:
        print("❌ Cancelled")
