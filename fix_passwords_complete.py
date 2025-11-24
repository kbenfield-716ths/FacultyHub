#!/usr/bin/env python3
"""
Complete fix for password hashing issue.
This will find and fix ALL passwords in your database.

Run this with your server STOPPED:
    python3 fix_passwords_complete.py
"""

import sqlite3
from passlib.context import CryptContext
from pathlib import Path
import shutil
from datetime import datetime

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
DEFAULT_PASSWORD = "PCCM2025!"

def find_database():
    """Find the database file"""
    possible_paths = [
        Path("./moonlighter.db"),
        Path("/data/moonlighter.db"),
        Path("../moonlighter.db"),
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    return None

def backup_database(db_path):
    """Create a backup of the database"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.parent / f"{db_path.stem}.backup.{timestamp}.db"
    shutil.copy2(db_path, backup_path)
    return backup_path

def fix_passwords(db_path):
    """Fix all passwords in the database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if faculty table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='faculty'")
        if not cursor.fetchone():
            print("❌ Faculty table not found in database")
            return False
        
        # Get all faculty
        cursor.execute("SELECT id, name, password_hash FROM faculty")
        all_faculty = cursor.fetchall()
        
        if not all_faculty:
            print("❌ No faculty found in database")
            return False
        
        print(f"\n📊 Found {len(all_faculty)} faculty members")
        print("-" * 60)
        
        # Check if passwords are already bcrypt
        new_hash = pwd_context.hash(DEFAULT_PASSWORD)
        sample_hash = all_faculty[0][2]
        
        # bcrypt hashes start with $2b$
        if sample_hash and sample_hash.startswith("$2b$"):
            print("✅ Passwords are already using bcrypt!")
            print("   If you're still getting errors, the issue might be elsewhere.")
            
            # Still rehash to be sure
            response = input("\nRehash anyway? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                return True
        
        print("\n🔧 Rehashing all passwords to bcrypt...")
        print("-" * 60)
        
        updated = 0
        for faculty_id, name, old_hash in all_faculty:
            # Generate new bcrypt hash
            new_hash = pwd_context.hash(DEFAULT_PASSWORD)
            
            # Update the password
            cursor.execute(
                "UPDATE faculty SET password_hash = ?, password_changed = 0 WHERE id = ?",
                (new_hash, faculty_id)
            )
            
            updated += 1
            print(f"✅ {name:30} ({faculty_id})")
        
        conn.commit()
        
        print("-" * 60)
        print(f"\n🎉 Successfully updated {updated} passwords!")
        print(f"🔐 All passwords are now: {DEFAULT_PASSWORD}")
        print("\n⚠️  Make sure to stop and restart your server!")
        
        return True
        
    except sqlite3.Error as e:
        print(f"\n❌ Database error: {e}")
        conn.rollback()
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    print("=" * 60)
    print("Faculty Hub - Password Hash Fix")
    print("=" * 60)
    print()
    
    # Find database
    print("🔍 Looking for database...")
    db_path = find_database()
    
    if not db_path:
        print("\n❌ Could not find database file!")
        print("\nPlease run this script from your project directory or specify:")
        db_input = input("Enter database path (or press Enter to cancel): ")
        if db_input:
            db_path = Path(db_input)
            if not db_path.exists():
                print(f"❌ File not found: {db_path}")
                return
        else:
            return
    
    print(f"✅ Found database: {db_path}")
    
    # Ask for confirmation
    print("\n⚠️  This will reset ALL faculty passwords to: PCCM2025!")
    response = input("Continue? (yes/no): ")
    
    if response.lower() not in ['yes', 'y']:
        print("❌ Cancelled")
        return
    
    # Backup database
    print("\n📦 Creating backup...")
    backup_path = backup_database(db_path)
    print(f"✅ Backup created: {backup_path}")
    
    # Fix passwords
    print()
    success = fix_passwords(db_path)
    
    if success:
        print("\n" + "=" * 60)
        print("✅ ALL DONE!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Restart your server if it's running")
        print("2. Try logging in with:")
        print("   - Faculty ID: (your faculty ID)")
        print("   - Password: PCCM2025!")
        print()
    else:
        print("\n" + "=" * 60)
        print("❌ Fix failed - database unchanged")
        print("=" * 60)
        print(f"\nBackup available at: {backup_path}")
        print()

if __name__ == "__main__":
    main()
