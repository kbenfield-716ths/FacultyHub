#!/usr/bin/env python3
"""
Migration script to add service week fields to Faculty table.

This adds:
- moonlighter (boolean) - whether faculty does moonlighting
- micu_weeks (int) - number of MICU weeks per year
- app_icu_weeks (int) - number of APP-ICU weeks per year
- procedure_weeks (int) - number of Procedure weeks per year
- consult_weeks (int) - number of Consult weeks per year

Run this after updating models.py but before starting the server.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from backend.models import engine

def run_migration():
    """Add new columns to faculty table if they don't exist"""
    
    print("[Migration] Adding service week fields to faculty table...")
    
    migrations = [
        ("moonlighter", "ALTER TABLE faculty ADD COLUMN moonlighter BOOLEAN DEFAULT 0"),
        ("micu_weeks", "ALTER TABLE faculty ADD COLUMN micu_weeks INTEGER DEFAULT 0"),
        ("app_icu_weeks", "ALTER TABLE faculty ADD COLUMN app_icu_weeks INTEGER DEFAULT 0"),
        ("procedure_weeks", "ALTER TABLE faculty ADD COLUMN procedure_weeks INTEGER DEFAULT 0"),
        ("consult_weeks", "ALTER TABLE faculty ADD COLUMN consult_weeks INTEGER DEFAULT 0"),
    ]
    
    with engine.connect() as conn:
        for column_name, sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"[Migration] ✓ Added column: {column_name}")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print(f"[Migration] ⊙ Column already exists: {column_name}")
                else:
                    print(f"[Migration] ✗ Error adding {column_name}: {e}")
                    raise
    
    print("[Migration] Migration complete!")
    print("\nNext steps:")
    print("1. Update faculty records with their service week commitments")
    print("2. Set moonlighter=True for faculty who do moonlighting shifts")
    print("3. Import historic data if needed")

if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"\n[Migration] FAILED: {e}")
        sys.exit(1)
