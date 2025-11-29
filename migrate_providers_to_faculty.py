#!/usr/bin/env python3
"""
Migration script to sync providers table with faculty table.

This script:
1. Checks what data exists in both providers and faculty tables
2. Syncs providers -> faculty (creates Faculty records for Provider records)
3. Optionally can sync faculty -> providers for consistency

Usage:
    python migrate_providers_to_faculty.py --check    # Just check what exists
    python migrate_providers_to_faculty.py --sync     # Sync providers to faculty
    python migrate_providers_to_faculty.py --rebuild  # Full rebuild from CSV
"""

import sys
import argparse
from pathlib import Path
from backend.models import SessionLocal, Provider, Faculty
from backend.auth import hash_password
import csv

def check_database():
    """Show what's in the database."""
    db = SessionLocal()
    try:
        providers = db.query(Provider).all()
        faculty = db.query(Faculty).all()
        
        print("\n" + "="*60)
        print("DATABASE STATUS CHECK")
        print("="*60)
        
        print(f"\n📊 PROVIDERS TABLE: {len(providers)} records")
        if providers:
            print("\nProviders:")
            for p in providers:
                print(f"  - {p.id:8s} | {p.name:30s} | {p.email or '(no email)'}")
        else:
            print("  (empty)")
        
        print(f"\n👤 FACULTY TABLE: {len(faculty)} records")
        if faculty:
            print("\nFaculty:")
            for f in faculty:
                admin_flag = " [ADMIN]" if f.is_admin else ""
                print(f"  - {f.id:8s} | {f.name:30s} | {f.email:30s}{admin_flag}")
        else:
            print("  (empty)")
        
        # Check for mismatches
        provider_ids = {p.id for p in providers}
        faculty_ids = {f.id for f in faculty}
        
        missing_in_faculty = provider_ids - faculty_ids
        missing_in_providers = faculty_ids - provider_ids
        
        print("\n🔍 SYNC STATUS:")
        if missing_in_faculty:
            print(f"  ⚠️  {len(missing_in_faculty)} providers NOT in faculty table: {missing_in_faculty}")
        if missing_in_providers:
            print(f"  ℹ️  {len(missing_in_providers)} faculty NOT in providers table: {missing_in_providers}")
        if not missing_in_faculty and not missing_in_providers and providers:
            print("  ✅ All providers have matching faculty records")
        
        print("\n" + "="*60 + "\n")
        
    finally:
        db.close()


def sync_providers_to_faculty(default_password="ChangeMe123!"):
    """Create Faculty records for all Providers that don't have them."""
    db = SessionLocal()
    try:
        providers = db.query(Provider).all()
        faculty_ids = {f.id for f in db.query(Faculty).all()}
        
        created = 0
        skipped = 0
        
        print("\n" + "="*60)
        print("SYNCING PROVIDERS → FACULTY")
        print("="*60 + "\n")
        
        for provider in providers:
            if provider.id in faculty_ids:
                print(f"⏭️  Skip {provider.id:8s} - already exists in faculty table")
                skipped += 1
                continue
            
            # Create faculty record
            faculty = Faculty(
                id=provider.id,
                name=provider.name,
                email=provider.email or f"{provider.id.lower()}@virginia.edu",
                password_hash=hash_password(default_password),
                password_changed=False,
                registered=True,
                is_admin=False,
                rank="associate",  # Default rank
                clinical_effort_pct=80,  # Default clinical effort
                base_points=100,  # Default starting points
                active=True
            )
            
            db.add(faculty)
            print(f"✅ Created {faculty.id:8s} | {faculty.name:30s} | {faculty.email}")
            created += 1
        
        if created > 0:
            db.commit()
            print(f"\n✅ Successfully created {created} faculty records")
            print(f"   Default password for all: {default_password}")
            print(f"   Users should change password on first login.\n")
        else:
            print(f"\n✅ No sync needed - all {skipped} providers already have faculty records\n")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error during sync: {e}\n")
        raise
    finally:
        db.close()


def rebuild_from_csv(csv_path="faculty.csv", default_password="ChangeMe123!"):
    """Rebuild both tables from faculty.csv file."""
    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"\n❌ CSV file not found: {csv_path}")
        print("   Expected format: computing_id,name,email,rank,clinical_effort")
        print("   Example: KE4Z,Dr. Kyle Enfield,ke4z@virginia.edu,associate,80\n")
        return
    
    db = SessionLocal()
    try:
        print("\n" + "="*60)
        print(f"REBUILDING FROM CSV: {csv_path}")
        print("="*60 + "\n")
        
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            
            created_providers = 0
            created_faculty = 0
            
            for row in reader:
                computing_id = row['computing_id'].strip().upper()
                name = row['name'].strip()
                email = row['email'].strip() if row.get('email') else f"{computing_id.lower()}@virginia.edu"
                rank = row.get('rank', 'associate').strip()
                clinical_effort = int(row.get('clinical_effort', 80))
                
                # Create or update Provider
                provider = db.query(Provider).filter_by(id=computing_id).first()
                if not provider:
                    provider = Provider(id=computing_id, name=name, email=email)
                    db.add(provider)
                    created_providers += 1
                    print(f"📋 Provider: {computing_id:8s} | {name:30s}")
                
                # Create or update Faculty
                faculty = db.query(Faculty).filter_by(id=computing_id).first()
                if not faculty:
                    faculty = Faculty(
                        id=computing_id,
                        name=name,
                        email=email,
                        password_hash=hash_password(default_password),
                        password_changed=False,
                        registered=True,
                        is_admin=False,
                        rank=rank,
                        clinical_effort_pct=clinical_effort,
                        base_points=100,
                        active=True
                    )
                    db.add(faculty)
                    created_faculty += 1
                    print(f"👤 Faculty:  {computing_id:8s} | {name:30s} | {email}")
        
        db.commit()
        print(f"\n✅ Created {created_providers} providers and {created_faculty} faculty records")
        print(f"   Default password: {default_password}\n")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error rebuilding from CSV: {e}\n")
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Migrate provider data to faculty table",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python migrate_providers_to_faculty.py --check
  python migrate_providers_to_faculty.py --sync
  python migrate_providers_to_faculty.py --sync --password "PCCM2025!"
  python migrate_providers_to_faculty.py --rebuild --csv faculty.csv
        """
    )
    
    parser.add_argument(
        '--check',
        action='store_true',
        help='Check database status (default if no action specified)'
    )
    
    parser.add_argument(
        '--sync',
        action='store_true',
        help='Sync providers to faculty table'
    )
    
    parser.add_argument(
        '--rebuild',
        action='store_true',
        help='Rebuild from CSV file'
    )
    
    parser.add_argument(
        '--csv',
        default='faculty.csv',
        help='CSV file path for --rebuild (default: faculty.csv)'
    )
    
    parser.add_argument(
        '--password',
        default='ChangeMe123!',
        help='Default password for new faculty accounts (default: ChangeMe123!)'
    )
    
    args = parser.parse_args()
    
    # Default to check if nothing specified
    if not (args.check or args.sync or args.rebuild):
        args.check = True
    
    try:
        if args.check:
            check_database()
        
        if args.sync:
            sync_providers_to_faculty(default_password=args.password)
            check_database()  # Show result
        
        if args.rebuild:
            rebuild_from_csv(csv_path=args.csv, default_password=args.password)
            check_database()  # Show result
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}\n")
        sys.exit(1)


if __name__ == '__main__':
    main()
