#!/usr/bin/env python3
"""
Import historic unavailability data from CSV.
This ONLY updates the historic_unavailable_count field on existing weeks.
Run this AFTER weeks have been generated.
"""

import sys
import os
import csv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from backend.models import SessionLocal, ServiceWeek

def import_historic_csv(csv_path):
    db = SessionLocal()
    
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            
            updates = 0
            missing = []
            
            for row in reader:
                week_number = int(row['week_number'])
                year = int(row['year'])
                unavailable_count = int(row['unavailable_count'])
                
                week_id = f"W{week_number:02d}-{year}"
                week = db.query(ServiceWeek).filter(ServiceWeek.id == week_id).first()
                
                if week:
                    week.historic_unavailable_count = unavailable_count
                    updates += 1
                else:
                    missing.append(week_id)
            
            db.commit()
            
            print(f"✅ Updated {updates} weeks with historic data")
            
            if missing:
                print(f"\n⚠️  Warning: {len(missing)} weeks not found in database:")
                for week_id in missing[:10]:  # Show first 10
                    print(f"   - {week_id}")
                if len(missing) > 10:
                    print(f"   ... and {len(missing) - 10} more")
                print("\n   Generate these weeks first with the admin panel or API")
            
    except FileNotFoundError:
        print(f"❌ Error: File not found: {csv_path}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 import_historic_csv.py <path_to_csv>")
        print("Example: python3 import_historic_csv.py historic_unavailability.csv")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    print(f"📊 Importing historic unavailability from: {csv_path}")
    print("=" * 60)
    
    success = import_historic_csv(csv_path)
    sys.exit(0 if success else 1)
