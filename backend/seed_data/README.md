# Historic Unavailability Data Seeding

This directory contains CSV files with historic unavailability data that gets automatically seeded into the database on startup.

## Purpose

For years before the system was deployed, we don't have actual faculty request data. Instead, we use historic CSV files to populate the `historic_unavailable_count` field in the `VacationWeek` table. This allows the heat map to display meaningful data for past years based on actual historical patterns.

Once the system is in production and faculty are making requests through the interface, future years will automatically use real request counts from the `VacationRequest` table.

## CSV Format

Each CSV file should be named: `unavailability_YYYY_YY.csv` (e.g., `unavailability_2025_26.csv` for the 2025-2026 academic year)

### Required columns:
- `week_number`: Week number from 1-52
- `unavailable_count`: Number of faculty who were unavailable that week

### Example:

```csv
week_number,unavailable_count
1,13
2,14
3,13
...
52,7
```

## How It Works

1. **On Startup**: The `seed_unavailability.py` script automatically runs during app startup
2. **Finds CSVs**: Scans this directory for files matching `unavailability_*.csv`
3. **Extracts Year**: Gets the academic year from the filename (first year of the academic year)
4. **Seeds Database**: Updates the `historic_unavailable_count` field for each week
5. **Heat Map Display**: The heat map API automatically uses historic counts when available, falling back to actual request counts for current/future years

## Adding New Historic Data

1. Create a new CSV file following the naming convention
2. Ensure weeks already exist in the database for that year (use the "Generate Weeks" admin tool first)
3. Restart the application or manually run: `python3 backend/seed_unavailability.py`

## Manual Seeding

You can also manually seed data:

```bash
cd backend
python3 seed_unavailability.py
```

## Data Source

Historic unavailability counts should come from:
- Previous scheduling systems
- Email records of time-off requests
- Calendar data from past years
- Administrative records

The goal is to capture the actual demand patterns from previous years to help with point cost calibration and staffing predictions.
