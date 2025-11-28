# Service Availability Configuration Guide

## Overview
The new service availability configuration system allows admins to:
1. Define special weeks (Christmas, conferences, etc.) with custom point values
2. Generate 52 weeks from a specified start date
3. Edit individual weeks after generation

## Access

Navigate to: `http://localhost:8000/admin-config.html`

## Three-Step Workflow

### Step 1: Configure Special Weeks

**Manual Configuration:**
- Click "+ Add Special Week" to create a new configuration
- Fill in:
  - **Name**: e.g., "Christmas", "ATS Conference"
  - **Date**: Middle of the period (e.g., Dec 25 for Christmas)
  - **Duration**: Number of weeks (1-4)
  - **Point Cost**: Points to be unavailable (default: 15)
  - **Point Reward**: Bonus points for volunteering (default: 20)

**Quick Presets:**
Click any preset button to auto-fill configurations:
- **Christmas** (2 weeks): -15 pts / +20 pts
- **Thanksgiving** (1 week): -15 pts / +20 pts
- **Spring Break** (1 week): -12 pts / +15 pts
- **ATS Conference** (1 week): -10 pts / +12 pts
- **CHEST Conference** (1 week): -10 pts / +12 pts
- **SCCM Conference** (1 week): -10 pts / +12 pts

### Step 2: Generate 52 Weeks

1. **Select Academic Year**: Choose from 2025-2028
2. **Set Start Date**: First Tuesday of July (e.g., July 7, 2026)
3. **Click "Generate 52 Weeks"**

The system will:
- Create 52 consecutive weeks starting from your date
- Automatically identify summer weeks (June-August): -7 pts / +5 pts
- Apply your special week configurations to matching dates
- Default regular weeks: -5 pts / +0 pts

### Step 3: Review and Edit

**View Generated Weeks:**
- Table shows all 52 weeks with:
  - Week number
  - Label (e.g., "Week 12 - Christmas")
  - Start/end dates
  - Type badge (Regular, Summer, Holiday, Conference)
  - Point costs and rewards
  - Minimum staff required
  - Number of requests

**Edit Any Week:**
- Click any cell to edit (except week number and requests)
- Press **Enter** to save
- Press **Escape** to cancel
- Changes save immediately to database

**Editable Fields:**
- Label
- Start Date
- End Date
- Point Cost (unavailable)
- Point Reward (volunteer)
- Min Staff Required

## Example Workflow

```
1. Click "Christmas (2 weeks)" preset
   → Auto-fills: Christmas, Dec 22, 2 weeks, -15/+20

2. Click "Thanksgiving" preset
   → Auto-fills: Thanksgiving, Nov 26, 1 week, -15/+20

3. Click "ATS Conference" preset
   → Auto-fills: ATS Conference, May 15, 1 week, -10/+12

4. Set Start Date: July 7, 2026
   → Academic year 2026-2027

5. Click "Generate 52 Weeks"
   → Creates full schedule with special weeks applied

6. Review table and edit as needed
   → Click "Week 25 - Spring Break" label to rename
   → Click point values to adjust
```

## Default Point Structure

- **Regular weeks**: -5 pts unavailable, +0 pts volunteer
- **Summer weeks**: -7 pts unavailable, +5 pts volunteer  
- **Special weeks**: Configured by admin (typically -10 to -15 pts / +12 to +20 pts)

## API Endpoints Used

### Generate Weeks
```
POST /api/admin/generate-service-weeks
{
  "year": 2026,
  "start_date": "2026-07-07",
  "special_weeks": [
    {
      "name": "Christmas",
      "date": "2026-12-25",
      "duration_weeks": 2,
      "point_cost": 15,
      "point_reward": 20
    }
  ]
}
```

### Update Week
```
PUT /api/admin/service-weeks/{week_id}
{
  "label": "Week 12 - Holiday Break",
  "point_cost_off": 20
}
```

### Get Weeks
```
GET /api/admin/service-weeks?year=2026
```

### Clear Weeks
```
DELETE /api/admin/service-weeks?year=2026
```

## Technical Details

**Week Generation Logic:**
1. Starts from specified date
2. Creates 52 consecutive 7-day weeks
3. For each week:
   - Checks if month is June-August → mark as "summer"
   - Checks if date matches any special week config → apply special settings
   - Otherwise → mark as "regular"
4. Generates unique ID: `W01-2026`, `W02-2026`, etc.
5. Saves to database with all point values

**Editable Week Updates:**
- Updates are immediate (no batch save)
- Only specified fields are updated
- Dates must be in ISO format (YYYY-MM-DD)
- Point values must be positive integers

## Future Enhancements

- Bulk edit multiple weeks at once
- Import/export configurations as JSON
- Copy configurations between years
- Visual calendar view of special weeks
- Validation warnings for conflicting dates
