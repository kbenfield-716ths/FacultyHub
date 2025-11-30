# Admin Panel Enhancements

This document describes the new features added to the admin panel for faculty and service week management.

## New Features

### 1. Enhanced Faculty Management

The faculty management page (`admin-faculty-tab.html`) now displays comprehensive information about each faculty member:

#### What's New:
- **Points Display**: Shows total points (base + bonus) for each faculty member
- **Service Week Assignments**: Displays count of weeks assigned by service type:
  - MICU (Medical ICU)
  - APP-ICU (APP ICU)
  - Procedures
  - Consults
- **Visual Badges**: Color-coded badges for easy identification of service types

#### How to Use:
1. Navigate to the "Manage Providers" tab in the admin panel
2. View the "Service Weeks" column showing assignment breakdown
3. See total weeks and individual service type counts

### 2. Service Week Assignment Tracking

New database model (`ServiceWeekAssignment`) tracks actual service assignments:

```python
class ServiceWeekAssignment:
    faculty_id: str          # Faculty member ID
    week_id: str            # Week identifier (e.g., "W01-2026")
    service_type: str       # "MICU", "APP-ICU", "Procedures", or "Consults"
    imported: bool          # True if from historic CSV import
```

### 3. Heat Map Visualization

New endpoint: `GET /api/admin/service-weeks/heatmap`

Visualizes staffing levels across all 52 weeks:
- **Green (Good)**: 3+ faculty above minimum required
- **Yellow (Tight)**: At minimum required staffing
- **Red (Critical)**: Below minimum required staffing
- **Blue Border**: Special weeks (holidays, conferences)

#### Displayed Information:
- Week number
- Number of faculty unavailable
- Number of volunteers
- Number assigned
- Staffing status

#### Access:
Use the new `admin-config-enhanced.html` page, "Heat Map" tab

### 4. Historic Data Import

New endpoint: `POST /api/admin/import-historic-assignments`

Import past service assignments from CSV files to:
1. Pre-populate faculty service history
2. Automatically mark premium weeks (weeks with historic assignments)
3. Set higher point costs for premium weeks

#### CSV Format:
```csv
faculty_id,week_number,service_type,year
KE4Z,1,MICU,2026
IN2C,2,APP-ICU,2026
JD3X,1,Procedures,2026
KE4Z,3,Consults,2026
```

#### Valid Service Types:
- `MICU`
- `APP-ICU`
- `Procedures`
- `Consults`

#### Import Process:
1. Navigate to `admin-config-enhanced.html`
2. Click "Import Historic Data" tab
3. Drag and drop CSV file or click to browse
4. Preview first 10 lines
5. Click "Import Assignments"

#### What Happens:
- Creates `ServiceWeekAssignment` records for each row
- Marks `imported = True` for tracking
- Automatically upgrades regular weeks to "premium" status if they have historic assignments
- Premium weeks get higher point costs (7 instead of 5)

### 5. Enhanced Configuration Interface

New file: `admin-config-enhanced.html`

Three-tab interface:

#### Tab 1: Heat Map
- Visual grid of all 52 weeks
- Color-coded staffing status
- Quick overview of availability
- Hover for detailed week information

#### Tab 2: Import Historic Data
- Drag-and-drop CSV upload
- File preview before import
- Error reporting with row-by-row validation
- Automatic premium week marking

#### Tab 3: Configure Weeks
- Generate 52-week schedule
- Configure special periods:
  - Christmas (2 weeks)
  - Thanksgiving
  - Spring Break
  - ATS Conference
  - CHEST Conference
  - SCCM Conference
- Set custom point costs and rewards
- Clear and regenerate schedules

## Database Changes

### New Table: `service_week_assignments`

```sql
CREATE TABLE service_week_assignments (
    id TEXT PRIMARY KEY,
    faculty_id TEXT NOT NULL,
    week_id TEXT NOT NULL,
    service_type TEXT NOT NULL,
    imported BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (faculty_id) REFERENCES faculty(id),
    FOREIGN KEY (week_id) REFERENCES vacation_weeks(id)
);
```

### Updated: `vacation_weeks`

Added support for assignment tracking via relationship:
```python
service_assignments = relationship("ServiceWeekAssignment", back_populates="week")
```

### Updated: `faculty`

Added support for assignment tracking via relationship:
```python
service_assignments = relationship("ServiceWeekAssignment", back_populates="faculty")
```

## API Endpoints

### GET /api/admin/faculty

**Enhanced Response:**
```json
{
  "id": "KE4Z",
  "name": "Kyle Enfield",
  "email": "kyle@example.com",
  "rank": "assistant",
  "clinical_effort_pct": 80,
  "base_points": 100,
  "bonus_points": 15,
  "total_points": 115,
  "active": true,
  "is_admin": true,
  "service_weeks": {
    "MICU": 4,
    "APP_ICU": 3,
    "Procedures": 2,
    "Consults": 1,
    "total": 10
  }
}
```

### GET /api/admin/service-weeks/heatmap

**Query Parameters:**
- `year` (int): Academic year (e.g., 2026)

**Response:**
```json
[
  {
    "week_id": "W01-2026",
    "week_number": 1,
    "label": "Week 1 (Jul 7)",
    "week_type": "regular",
    "unavailable_count": 2,
    "volunteer_count": 0,
    "assigned_count": 5,
    "min_staff_required": 5,
    "staffing_status": "good"
  }
]
```

### POST /api/admin/import-historic-assignments

**Request:**
- Content-Type: `multipart/form-data`
- Body: CSV file

**Response:**
```json
{
  "success": true,
  "assignments_created": 150,
  "weeks_marked_premium": 12,
  "errors": [
    "Row 5: Faculty ABC not found",
    "Row 12: Invalid service type 'ICU'"
  ],
  "message": "Imported 150 assignments with 2 errors"
}
```

## Usage Examples

### Example 1: Viewing Faculty Service History

1. Log in as admin
2. Navigate to "Manage Providers" tab
3. View the "Service Weeks" column
4. See breakdown: MICU: 4, APP-ICU: 3, etc.
5. Total weeks assigned: 10

### Example 2: Importing Historic Assignments

1. Prepare CSV file:
   ```csv
   faculty_id,week_number,service_type,year
   KE4Z,1,MICU,2026
   KE4Z,5,MICU,2026
   KE4Z,10,MICU,2026
   IN2C,2,APP-ICU,2026
   ```

2. Navigate to `admin-config-enhanced.html`
3. Click "Import Historic Data" tab
4. Upload CSV file
5. Review preview
6. Click "Import Assignments"
7. System automatically marks weeks 1, 2, 5, 10 as premium

### Example 3: Viewing Heat Map

1. Navigate to `admin-config-enhanced.html`
2. Select academic year (2026-2027)
3. View grid of 52 weeks
4. Identify critical weeks (red)
5. Plan recruitment or adjust schedules

### Example 4: Generating Weeks with Premium Periods

1. Navigate to "Configure Weeks" tab
2. Set academic year: 2026-2027
3. Set start date: 2026-07-07
4. Configure special dates:
   - Christmas: 2026-12-22
   - Thanksgiving: 2026-11-26
5. Click "Generate 52 Weeks"
6. Switch to "Heat Map" to visualize
7. Import historic data to mark additional premium weeks

## Premium Week System

### What Makes a Week Premium?

A week becomes "premium" when:
1. Manually configured as a special period (Christmas, Thanksgiving, etc.)
2. Has historic service assignments imported from CSV

### Premium Week Benefits:

**For System:**
- Identifies high-demand periods
- Tracks historically difficult-to-staff weeks
- Enables data-driven scheduling

**For Faculty:**
- Higher point costs reflect difficulty
- Higher rewards for volunteering
- Fair compensation for working premium periods

### Point Structure:

| Week Type | Cost (Unavailable) | Reward (Volunteer) |
|-----------|-------------------|--------------------|
| Regular   | 5 points          | 0 points           |
| Premium   | 7 points          | 5 points           |
| Summer    | 7 points          | 5 points           |
| Holiday   | 15 points         | 20 points          |
| Conference| 10-15 points      | 12-20 points       |

## Troubleshooting

### CSV Import Errors

**Error: "Faculty X not found"**
- Solution: Add faculty member first via "Manage Providers"

**Error: "Invalid service type"**
- Solution: Use only: MICU, APP-ICU, Procedures, Consults

**Error: "Week not found"**
- Solution: Generate weeks first via "Configure Weeks"

### Heat Map Issues

**Heat map shows "No weeks configured"**
- Solution: Generate weeks using Configure tab

**Incorrect staffing colors**
- Check minimum staff requirements per week
- Verify faculty active status
- Ensure unavailability requests are submitted

## Migration Guide

### From Legacy System

1. **Export historic assignments** to CSV format
2. **Generate weeks** for new academic year
3. **Import historic data** to mark premium weeks
4. **Add faculty** if not already in system
5. **Review heat map** to verify staffing

### Database Migration

The system automatically creates the new table on startup:
```bash
python backend/app.py
```

No manual migration required.

## Best Practices

1. **Import historic data early** to identify premium weeks before faculty make requests
2. **Generate weeks at least 3 months** before academic year starts
3. **Review heat map weekly** during request period
4. **Keep CSV backups** of all imports
5. **Validate faculty IDs** before bulk imports

## Future Enhancements

Potential additions:
- Automatic premium week detection based on request patterns
- Export assignments to CSV
- Multi-year heat map comparison
- Predictive staffing analytics
- Email notifications for critical weeks
