# Critical Fixes: Faculty Fields and Historic Data Loading

## Issues Fixed

This branch addresses three critical issues in the PCCM Faculty Hub system:

### 1. Missing Faculty Service Week Fields
**Problem**: The Faculty table was missing fields needed for inpatient schedule building:
- `moonlighter` (boolean) - whether faculty participates in moonlighting
- `micu_weeks` (int) - number of MICU weeks per year
- `app_icu_weeks` (int) - number of APP-ICU weeks per year  
- `procedure_weeks` (int) - number of Procedure weeks per year
- `consult_weeks` (int) - number of Consult weeks per year

**Solution**: Added these fields to the Faculty model. These are essential for the eventual scheduler to know how many weeks each faculty member should be assigned to each service type.

### 2. Historic Data Not Loading in Heatmap
**Problem**: The heatmap endpoint only showed data when `historic_unavailable_count > 0`, but the CSV import for historic assignments wasn't populating this field.

**Solution**: 
- Updated the historic assignments import to automatically calculate and set `historic_unavailable_count` for each week based on who was working
- Added a separate endpoint and script for directly importing historic unavailability counts
- Fixed heatmap logic to properly use historic data when available

### 3. No Way to Import Historic Unavailability
**Problem**: There was no mechanism to seed historic unavailability data for years before system deployment (e.g., 2025-2026).

**Solution**: Created two methods to import historic data:
1. Import historic assignments (infers unavailability from who was NOT assigned)
2. Direct import of unavailability counts per week

## Migration Steps

### Step 1: Update Database Schema

Run the migration script to add new columns to existing Faculty table:

```bash
cd backend
python scripts/migrate_add_faculty_fields.py
```

This will add:
- `moonlighter` (defaults to FALSE)
- `micu_weeks` (defaults to 0)
- `app_icu_weeks` (defaults to 0)
- `procedure_weeks` (defaults to 0)
- `consult_weeks` (defaults to 0)

### Step 2: Update Faculty Records

You'll need to update each faculty member's service week commitments. This can be done via:

1. **Admin UI** (once deployed): Edit each faculty member to set their service week counts
2. **Direct SQL** (for bulk updates):

```sql
UPDATE faculty 
SET micu_weeks = 4, 
    app_icu_weeks = 2, 
    procedure_weeks = 3, 
    consult_weeks = 0,
    moonlighter = 1
WHERE id = 'KE4Z';
```

3. **Python script**:

```python
from backend.models import SessionLocal, Faculty

db = SessionLocal()

# Example: Set Dr. Benfield's service weeks
faculty = db.query(Faculty).filter_by(id='KE4Z').first()
faculty.micu_weeks = 4
faculty.app_icu_weeks = 2  
faculty.procedure_weeks = 3
faculty.consult_weeks = 0
faculty.moonlighter = True

db.commit()
```

### Step 3: Generate Service Weeks

If you haven't already, generate the 52 weeks for your academic year(s):

```bash
# Via API (as admin):
POST /api/admin/generate-service-weeks
{
    "year": 2026,
    "start_date": "2026-07-07",
    "summer_start": "2026-06-01",
    "summer_end": "2026-08-31",
    "thanksgiving": "2026-11-26",
    "christmas": "2026-12-24"
}
```

### Step 4: Import Historic Data

You have two options for importing historic data:

#### Option A: Import Historic Assignments (Recommended)

If you have historic assignment data showing who was assigned to which service each week:

**CSV Format** (`historic_assignments.csv`):
```csv
faculty_id,week_number,service_type,year
KE4Z,1,MICU,2025
IN2C,1,APP-ICU,2025
KE4Z,2,Procedures,2025
...
```

**Import via API**:
```bash
POST /api/admin/import-historic-assignments
Content-Type: multipart/form-data
file: historic_assignments.csv
```

This will:
1. Create ServiceWeekAssignment records for each assignment
2. Automatically calculate `historic_unavailable_count` for each week
   - Calculation: `total_active_faculty - faculty_assigned_that_week`

#### Option B: Direct Import of Unavailability Counts

If you have pre-calculated unavailability counts per week:

**CSV Format** (`historic_unavailability.csv`):
```csv
week_number,year,unavailable_count
1,2025,8
2,2025,5
3,2025,12
...
```

**Import via API**:
```bash
POST /api/admin/import-historic-unavailability
Content-Type: multipart/form-data
file: historic_unavailability.csv
```

**Or via Python script**:
```bash
cd backend/scripts
python import_historic_unavailability.py import ../path/to/historic_unavailability.csv
```

**To export a template**:
```bash
python import_historic_unavailability.py export historic_template.csv
```

## Verification

### Check Faculty Fields

```sql
SELECT id, name, moonlighter, micu_weeks, app_icu_weeks, procedure_weeks, consult_weeks 
FROM faculty 
WHERE active = 1;
```

### Check Historic Data Loaded

```sql
-- Check historic assignments
SELECT COUNT(*) as assignment_count, week_id 
FROM service_week_assignments 
WHERE imported = 1 
GROUP BY week_id;

-- Check historic unavailability counts
SELECT week_number, year, historic_unavailable_count 
FROM service_weeks 
WHERE historic_unavailable_count > 0 
ORDER BY year, week_number;
```

### Test Heatmap

Access the heatmap endpoint (as admin):
```bash
GET /api/admin/service-weeks/heatmap?year=2025
```

Should return data like:
```json
[
  {
    "week_id": "W01-2025",
    "week_number": 1,
    "label": "Week 1 (Jul 7)",
    "week_type": "summer",
    "unavailable_count": 8,
    "volunteer_count": 0,
    "assigned_count": 12,
    "min_staff_required": 5,
    "staffing_status": "good"
  },
  ...
]
```

## How the System Works Now

### Availability vs. Assignment System

This is an **availability system**, not a vacation system. The workflow is:

1. **Faculty indicate UNAVAILABILITY** (not vacation requests)
   - "I cannot work service week 15" (costs points)
   - "I'm willing to work Christmas week" (earns bonus points)

2. **System tracks who CAN work** each week
   - Based on who is NOT unavailable
   - Considers service week commitments (micu_weeks, app_icu_weeks, etc.)

3. **Schedule builder uses availability data**
   - Knows each faculty member's service commitments
   - Knows when each faculty member is unavailable
   - Can optimize assignments accordingly

### Historic Data for Past Years

For years before system deployment (e.g., 2025-2026):

- **Historic assignments** show who actually worked each week last year
- **Historic unavailability counts** show how many faculty were unavailable
- **Heatmap displays this data** so you can see patterns from previous years
- Helps identify traditionally difficult weeks to staff

### Current/Future Year Data

For the current academic year and beyond:

- Faculty actively request unavailability through the system
- System calculates point costs based on demand pressure
- Admin sees real-time staffing status via heatmap
- Historic data is NOT used (actual requests are displayed)

## Database Schema Changes

### Before
```sql
CREATE TABLE faculty (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    rank TEXT NOT NULL,
    clinical_effort_pct INTEGER NOT NULL,
    base_points INTEGER NOT NULL,
    bonus_points INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT 1
);
```

### After
```sql
CREATE TABLE faculty (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    rank TEXT NOT NULL,
    clinical_effort_pct INTEGER NOT NULL,
    base_points INTEGER NOT NULL,
    bonus_points INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT 1,
    moonlighter BOOLEAN DEFAULT 0,        -- NEW
    micu_weeks INTEGER DEFAULT 0,         -- NEW
    app_icu_weeks INTEGER DEFAULT 0,      -- NEW
    procedure_weeks INTEGER DEFAULT 0,    -- NEW
    consult_weeks INTEGER DEFAULT 0       -- NEW
);
```

## Next Steps

After completing this migration:

1. ✓ Faculty table has service week fields
2. ✓ Historic data can be imported and displayed
3. ✓ Heatmap works for both historic and current data

**Future development**:
- Build the actual schedule optimizer
- Use faculty service week commitments to assign service weeks
- Respect unavailability requests when building schedules
- Integrate moonlighter status for IRPA shift assignments

## Troubleshooting

### Migration fails with "duplicate column"
The columns already exist. This is safe to ignore - the migration script handles this gracefully.

### Heatmap shows zero unavailable even after import
1. Check that weeks were generated: `SELECT COUNT(*) FROM service_weeks;`
2. Check historic data: `SELECT COUNT(*) FROM service_weeks WHERE historic_unavailable_count > 0;`
3. Verify year parameter matches imported data

### Historic assignments import shows errors
Common issues:
- **Faculty not found**: Create faculty members first
- **Weeks not found**: Generate weeks for that year first  
- **Invalid service type**: Must be exactly "MICU", "APP-ICU", "Procedures", or "Consults"

### Can't see providers in frontend
The `Provider` table (for moonlighting) is separate from `Faculty` table. If you need to sync them:

```python
from backend.models import SessionLocal, Faculty, Provider

db = SessionLocal()

# Create Provider records for faculty who moonlight
faculty_list = db.query(Faculty).filter_by(moonlighter=True).all()
for faculty in faculty_list:
    provider = db.query(Provider).filter_by(id=faculty.id).first()
    if not provider:
        provider = Provider(
            id=faculty.id,
            name=faculty.name,
            email=faculty.email
        )
        db.add(provider)

db.commit()
```

## Questions?

Contact: Kyle Benfield (KE4Z)
