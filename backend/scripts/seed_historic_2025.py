#!/usr/bin/env python3
"""
Seed historic data for 2025-2026 academic year.
This creates:
1. Service weeks for 2025-2026 (July 1, 2025 - June 30, 2026)
2. Historic unavailability counts to show in heatmap
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from datetime import datetime, timedelta
from backend.models import SessionLocal, ServiceWeek, Faculty
from sqlalchemy import func
import random

def seed_historic_2025():
    db = SessionLocal()
    
    try:
        # Check if weeks already exist
        existing = db.query(ServiceWeek).filter(ServiceWeek.year == 2025).count()
        if existing > 0:
            print(f"✅ 2025 weeks already exist ({existing} weeks). Updating unavailability counts...")
        else:
            print("📅 Creating 2025-2026 service weeks...")
            
            # Academic year 2025-2026 starts July 1, 2025
            start_date = datetime(2025, 7, 1).date()
            
            # Find the first Tuesday on or after July 1
            days_until_tuesday = (1 - start_date.weekday()) % 7  # Tuesday is 1
            if days_until_tuesday > 0:
                start_date = start_date + timedelta(days=days_until_tuesday)
            
            current_date = start_date
            
            for week_num in range(1, 53):
                end_date = current_date + timedelta(days=6)
                
                # Default values
                week_type = "regular"
                point_cost_off = 5
                point_reward_work = 0
                label = f"Week {week_num} ({current_date.strftime('%b %d')})"
                
                # Summer weeks (June, July, August)
                if current_date.month in [6, 7, 8]:
                    week_type = "summer"
                    point_cost_off = 7
                    point_reward_work = 5
                    label = f"Week {week_num} - Summer ({current_date.strftime('%b %d')})"
                
                # Special weeks (approximate dates)
                # Thanksgiving (week 21 - around late November)
                if week_num in [21, 22]:
                    week_type = "thanksgiving"
                    point_cost_off = 15
                    point_reward_work = 20
                    label = f"Week {week_num} - Thanksgiving ({current_date.strftime('%b %d')})"
                
                # Christmas/New Year (weeks 26-27 - late December/early January)
                elif week_num in [26, 27]:
                    week_type = "christmas"
                    point_cost_off = 15
                    point_reward_work = 25
                    label = f"Week {week_num} - Winter Holiday ({current_date.strftime('%b %d')})"
                
                # Spring Break (week 38 - around March)
                elif week_num == 38:
                    week_type = "spring_break"
                    point_cost_off = 10
                    point_reward_work = 15
                    label = f"Week {week_num} - Spring Break ({current_date.strftime('%b %d')})"
                
                # ATS Conference (week 45 - May)
                elif week_num == 45:
                    week_type = "ats_conference"
                    point_cost_off = 15
                    point_reward_work = 20
                    label = f"Week {week_num} - ATS Conference ({current_date.strftime('%b %d')})"
                
                week = ServiceWeek(
                    id=f"W{week_num:02d}-2025",
                    week_number=week_num,
                    label=label,
                    start_date=current_date,
                    end_date=end_date,
                    year=2025,
                    week_type=week_type,
                    point_cost_off=point_cost_off,
                    point_reward_work=point_reward_work,
                    min_staff_required=5,
                    historic_unavailable_count=0
                )
                
                db.add(week)
                current_date = current_date + timedelta(days=7)
            
            db.commit()
            print(f"✅ Created 52 weeks for 2025-2026")
        
        # Now seed realistic historic unavailability counts
        print("📊 Seeding historic unavailability data...")
        
        total_faculty = db.query(func.count(Faculty.id)).filter(Faculty.active == True).scalar() or 20
        weeks_2025 = db.query(ServiceWeek).filter(ServiceWeek.year == 2025).order_by(ServiceWeek.week_number).all()
        
        for week in weeks_2025:
            # Base unavailability varies by week type
            if week.week_type == "summer":
                # More people unavailable in summer
                base_unavailable = random.randint(8, 12)
            elif week.week_type in ["christmas", "thanksgiving", "spring_break"]:
                # Very popular times - many want off
                base_unavailable = random.randint(10, 15)
            elif week.week_type in ["ats_conference"]:
                # Conference weeks - moderate unavailability
                base_unavailable = random.randint(6, 10)
            else:
                # Regular weeks - normal unavailability
                base_unavailable = random.randint(3, 7)
            
            # Add some randomness
            unavailable_count = min(base_unavailable + random.randint(-2, 2), total_faculty - 3)
            unavailable_count = max(unavailable_count, 2)  # At least 2 unavailable
            
            week.historic_unavailable_count = unavailable_count
        
        db.commit()
        
        # Print summary
        print("\n📈 Historic Data Summary for 2025-2026:")
        print(f"   Total weeks: {len(weeks_2025)}")
        
        week_types = {}
        for week in weeks_2025:
            week_type = week.week_type
            if week_type not in week_types:
                week_types[week_type] = []
            week_types[week_type].append(week.historic_unavailable_count)
        
        for week_type, counts in sorted(week_types.items()):
            avg = sum(counts) / len(counts)
            print(f"   {week_type}: {len(counts)} weeks, avg {avg:.1f} unavailable")
        
        print("\n✅ Historic data seeded successfully!")
        print("   You can now view the 2025 heatmap to see historic patterns")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("🏥 PCCM Faculty Hub - Seed Historic 2025 Data")
    print("=" * 60)
    seed_historic_2025()
