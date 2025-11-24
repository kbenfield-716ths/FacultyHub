#!/usr/bin/env python3
"""
Direct fix using bcrypt library (not passlib)
This WILL work.
"""
import sqlite3
import bcrypt
from datetime import datetime
import shutil
from pathlib import Path

DEFAULT_PASSWORD = "PCCM2025!"

def backup_database(db_path):
    """Create backup"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup.{timestamp}"
    shutil.copy2(db_path, backup_path)
    return backup_path

def fix_passwords():
    """Fix all passwords using bcrypt directly"""
    db_path = "moonlighter.db"
    
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        return False
    
    print("=" * 60)
    print("Direct Password Fix with bcrypt")
    print("=" * 60)
    print()
    
    # Backup
    print("📦 Creating backup...")
    backup_path = backup_database(db_path)
    print(f"✅ Backup: {backup_path}")
    print()
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get all faculty
        cursor.execute("SELECT id, name, password_hash FROM faculty")
        all_faculty = cursor.fetchall()
        
        print(f"Found {len(all_faculty)} faculty members")
        print("-" * 60)
        
        # Generate ONE bcrypt hash for the default password
        # This is the correct way to do it
        salt = bcrypt.gensalt()
        new_hash = bcrypt.hashpw(DEFAULT_PASSWORD.encode('utf-8'), salt)
        new_hash_str = new_hash.decode('utf-8')
        
        print(f"Generated bcrypt hash: {new_hash_str[:30]}...")
        print()
        
        # Update all faculty with the same hash
        updated = 0
        for faculty_id, name, old_hash in all_faculty:
            cursor.execute(
                "UPDATE faculty SET password_hash = ?, password_changed = 0 WHERE id = ?",
                (new_hash_str, faculty_id)
            )
            updated += 1
            print(f"✅ {name:30} ({faculty_id})")
        
        # Commit changes
        conn.commit()
        
        print("-" * 60)
        print(f"\n🎉 Updated {updated} passwords!")
        print(f"🔐 Password: {DEFAULT_PASSWORD}")
        print("\n✅ Done! Restart your server and try logging in.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print()
    response = input("This will reset ALL passwords. Continue? (yes/no): ")
    if response.lower() == 'yes':
        fix_passwords()
    else:
        print("Cancelled")
