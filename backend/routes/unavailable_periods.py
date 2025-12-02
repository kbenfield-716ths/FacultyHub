# backend/routes/unavailable_periods.py
"""
DEPRECATED: This file is not in use.

The original implementation referenced an 'UnavailablePeriod' model that was never
created in models.py. The system now uses:
- ServiceWeek: For defining the 52-week schedule
- UnavailabilityRequest: For faculty availability requests

This file is kept for reference but the router is not registered in app.py.
If you need this functionality, either:
1. Create the UnavailablePeriod model in models.py
2. Or adapt this to use the existing ServiceWeek/UnavailabilityRequest models

Original functionality was intended for:
- Creating date-range-based unavailability periods (vs week-based)
- Supporting both provider-specific and global calendar blocks
"""

# Router not registered - file kept for reference only
