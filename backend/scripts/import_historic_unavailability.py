#!/usr/bin/env python3
"""
Import historic unavailability data to populate heatmap.

CSV Format:
week_number,year,unavailable_count
1,2025,8
2,2025,5
3,2025,12
...

This populates the historic_unavailable_count field on ServiceWeek records,
which is used by the heatmap endpoint for years before the system was deployed.
"""

import sys
import os
import csv
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models import SessionLocal, ServiceWeek

def import_historic_unavailability(csv_file_path):
    """Import historic unavailability counts from CSV"""
    
    if not os.path.exists(csv_file_path):
        print(f"Error: File not found: {csv_file_path}")
        return False
    
    db = SessionLocal()
    
    try:
        print(f"[Import] Reading: {csv_file_path}")
        
        with open(csv_file_path, 'r') as f:
            reader = csv.DictReader(f)
            
            # Validate headers
            required_cols = {'week_number', 'year', 'unavailable_count'}
            if not required_cols.issubset(set(reader.fieldnames or [])):
                print(f"Error: CSV must have columns: {', '.join(required_cols)}")
                return False
            
            updated_count = 0
            created_count = 0
            error_count = 0
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    week_number = int(row['week_number'])
                    year = int(row['year'])
                    unavailable_count = int(row['unavailable_count'])
                    
                    # Validate week number
                    if not 1 <= week_number <= 52:
                        print(f"Row {row_num}: Invalid week number {week_number} (must be 1-52)")
                        error_count += 1
                        continue
                    
                    # Find week
                    week_id = f"W{week_number:02d}-{year}"
                    week = db.query(ServiceWeek).filter_by(id=week_id).first()
                    
                    if not week:
                        print(f"Row {row_num}: Week {week_number} for year {year} not found - will be created on week generation")
                        error_count += 1
                        continue
                    
                    # Update historic unavailable count
                    week.historic_unavailable_count = unavailable_count
                    updated_count += 1
                    
                    if row_num % 10 == 0:
                        print(f"[Import] Processed {row_num} rows...")
                    
                except ValueError as e:
                    print(f"Row {row_num}: Invalid number format - {e}")
                    error_count += 1
                    continue
                except Exception as e:
                    print(f"Row {row_num}: Error - {e}")
                    error_count += 1
                    continue
            
            db.commit()
            
            print(f"\n[Import] Complete!")
            print(f"  ✓ Updated: {updated_count} weeks")
            if error_count:
                print(f"  ✗ Errors: {error_count} rows")
            
            return True
            
    except Exception as e:
        print(f"[Import] Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def export_template(output_file="historic_unavailability_template.csv"):
    """Export a template CSV with current weeks"""
    
    db = SessionLocal()
    
    try:
        print(f"[Export] Creating template: {output_file}")
        
        weeks = db.query(ServiceWeek).order_by(ServiceWeek.year, ServiceWeek.week_number).all()
        
        if not weeks:
            print("No weeks found in database. Generate weeks first.")
            return False
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['week_number', 'year', 'unavailable_count'])
            
            for week in weeks:
                # Pre-fill with current value or 0
                writer.writerow([
                    week.week_number,
                    week.year,
                    week.historic_unavailable_count
                ])
        
        print(f"[Export] Template created with {len(weeks)} weeks")
        print(f"Fill in the unavailable_count column and re-import")
        return True
        
    except Exception as e:
        print(f"[Export] Error: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Import: python import_historic_unavailability.py import <csv_file>")
        print("  Export template: python import_historic_unavailability.py export [output_file]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "import":
        if len(sys.argv) < 3:
            print("Error: Please specify CSV file to import")
            sys.exit(1)
        csv_file = sys.argv[2]
        success = import_historic_unavailability(csv_file)
        sys.exit(0 if success else 1)
        
    elif command == "export":
        output_file = sys.argv[2] if len(sys.argv) > 2 else "historic_unavailability_template.csv"
        success = export_template(output_file)
        sys.exit(0 if success else 1)
        
    else:
        print(f"Unknown command: {command}")
        print("Use 'import' or 'export'")
        sys.exit(1)
