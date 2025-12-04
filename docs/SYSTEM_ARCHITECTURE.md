# PCCM Faculty Hub - Complete System Architecture

## Core Principle
**This is an AVAILABILITY system** - Faculty request when they CAN'T work, not when they want vacation.

## System Components

### 1. DATA MODEL (Single Source of Truth)

#### Faculty Table (PRIMARY)
```
- id (computing ID: KE4Z, IN2C, etc.)
- name
- email
- rank (assistant/associate/full)
- clinical_effort_pct
- base_points
- bonus_points
- active (boolean)
- is_admin (boolean)
- password_hash
- password_changed
- registered
- moonlighter (boolean) - participates in moonlighting?
- micu_weeks (int) - expected MICU weeks per year
- app_icu_weeks (int) - expected APP-ICU weeks per year
- procedure_weeks (int) - expected Procedure weeks per year
- consult_weeks (int) - expected Consult weeks per year
```

#### Provider Table (LEGACY - for moonlighting only)
```
- id
- name  
- email
```
**Note:** This table is ONLY for the moonlighting shift system. Most faculty will NOT be in this table.

#### ServiceWeek Table (52 weeks per academic year)
```
- id (W01-2026, W02-2026, etc.)
- week_number (1-52)
- label ("Week 1 (Jul 7)")
- start_date
- end_date
- year
- week_type (regular/summer/spring_break/thanksgiving/christmas)
- point_cost_off (cost to request unavailability)
- point_reward_work (bonus for volunteering)
- min_staff_required
- historic_unavailable_count (from imported data)
```

#### UnavailabilityRequest Table
```
- faculty_id
- week_id
- status (unavailable/available/assigned)
- points_spent
- points_earned
```

#### ServiceWeekAssignment Table (Actual schedule)
```
- faculty_id
- week_id
- service_type (MICU/APP-ICU/Procedures/Consults)
- imported (boolean - true if historic data)
```

### 2. ADMIN INTERFACE REQUIREMENTS

#### Tab 1: Manage Faculty
**Display Columns:**
- ID (computing ID)
- Name
- Email
- Admin (Y/N checkbox)
- Moonlighter (Y/N checkbox)
- MICU Weeks (editable number)
- APP-ICU Weeks (editable number)
- Procedure Weeks (editable number)
- Consult Weeks (editable number)
- Actions (Edit/Delete buttons)

**Features:**
- Add new faculty
- Edit inline
- Toggle admin status
- Toggle moonlighter status
- Set service week commitments
- Activate/deactivate faculty

**API Endpoint:** GET/POST/PATCH /api/admin/faculty

#### Tab 2: Moonlighting/IRPA
**Status:** WORKING - DO NOT MODIFY
- This is the existing moonlighting shift system
- Uses Provider table
- Separate from service availability

#### Tab 3: Service Overview (Current Year Heatmap)
**Purpose:** Show which weeks have high unavailability requests for CURRENT academic year

**Display:**
- 52-week calendar view
- Color coding:
  - Green: Low unavailability (plenty of staff available)
  - Yellow: Medium unavailability (tight staffing)
  - Red: High unavailability (critical staffing)
- Show for current academic year only
- Hover to see: week dates, # unavailable, # volunteered, staffing status

**Data Source:** 
- Count actual UnavailabilityRequest records where status="unavailable"
- For current/future years only

**API Endpoint:** GET /api/admin/service-weeks/heatmap?year=2026

#### Tab 4: Configure Periods
**Two Sub-sections:**

**4a. Historic Data View**
- Show PREVIOUS academic year heatmap (e.g., if working on 2026-2027, show 2025-2026)
- Purpose: See patterns from last year to inform current year planning
- Data source: historic_unavailable_count field (from imported CSV)
- Display: Same heatmap format as Tab 3

**4b. Generate Weeks**
- Form to generate 52 weeks for a new academic year
- Inputs:
  - Academic year (2026, 2027, etc.)
  - Start date (first Monday after July 1)
  - Holiday weeks (mark as special)
- Button: "Generate Weeks"
- **CRITICAL:** Do NOT delete existing weeks or historic data
- Generate with format: W01-2026, W02-2026, etc.

**API Endpoints:**
- GET /api/admin/service-weeks/heatmap?year=2025 (historic)
- POST /api/admin/generate-service-weeks

#### Tab 5: View Requests
**Purpose:** See unavailability requests by faculty

**Display:**
- Filter by: Faculty, Week, Status
- Table showing:
  - Faculty Name
  - Week
  - Status (Unavailable/Available/Assigned)
  - Points Spent
  - Points Earned
  - Date Requested

**API Endpoint:** GET /api/admin/service-requests

#### Tab 6: Manage Weeks
**Purpose:** Adjust week settings

**Display:**
- Table of all weeks
- Editable columns:
  - Week number
  - Start date
  - End date
  - Week type (dropdown)
  - Point cost off
  - Point reward work
  - Min staff required

**API Endpoint:** GET/PATCH /api/admin/service-weeks/{week_id}

#### Tab 7: Build Schedule (FUTURE)
**Purpose:** Generate actual service assignments

**Features:**
- Respect unavailability requests
- Match faculty service commitments (micu_weeks, app_icu_weeks, etc.)
- Create ServiceWeekAssignment records
- Export schedule

**API Endpoint:** POST /api/admin/build-schedule

### 3. CRITICAL FIXES NEEDED

#### Fix 1: Remove Provider/Faculty Duplication
**Problem:** Admin interface shows both "Providers" and "Faculty"

**Solution:**
- Remove ALL references to "Manage Providers" from admin interface
- Use ONLY "Manage Faculty" tab
- Provider table remains for moonlighting but isn't shown in main admin

**Files to Update:**
- admin.html (remove provider section)

#### Fix 2: Display New Faculty Fields
**Problem:** API returns new fields but UI doesn't show them

**Solution:**
- Update admin.html to show: moonlighter, micu_weeks, app_icu_weeks, procedure_weeks, consult_weeks
- Make fields editable inline or via edit form
- Use checkboxes for boolean fields

**Files to Update:**
- admin.html (faculty table rendering)

#### Fix 3: Heatmap Shows Historic vs Current Data Correctly
**Problem:** Heatmap logic confused about when to use historic_unavailable_count vs actual requests

**Solution:**
```python
# In heatmap endpoint:
if week.historic_unavailable_count > 0:
    # Use historic data (for years before system deployed)
    unavailable_count = week.historic_unavailable_count
else:
    # Use actual requests (for current/future years)
    unavailable_count = count of UnavailabilityRequests where status="unavailable"
```

**Files to Update:**
- backend/routes/admin_service.py (heatmap endpoint)

#### Fix 4: Week Generation Doesn't Delete Historic Data
**Problem:** Generating new weeks might delete existing week data

**Solution:**
- Check if week already exists before creating
- Never delete existing ServiceWeek records
- Never delete historic_unavailable_count data
- Only create weeks that don't exist

**Files to Update:**
- backend/routes/admin_service.py (generate weeks endpoint)

#### Fix 5: Academic Year Calendar (July-June)
**Problem:** System might default to calendar year

**Solution:**
- Always start weeks on first Monday on or after July 1
- Week 1 = first week of July
- Week 52 ends in late June
- Year field = year that July falls in (2026-2027 academic year = year 2026)

**Files to Update:**
- backend/routes/admin_service.py (week generation logic)
- admin.html (year selector shows academic years)

### 4. FILE STRUCTURE

```
backend/
├── models.py (✓ CORRECT - has all fields)
├── routes/
│   ├── admin_faculty.py (✓ FIXED - returns new fields)
│   ├── admin_service.py (needs heatmap + generation fixes)
│   └── providers.py (for moonlighting only)
├── auth.py
└── app.py

frontend/
├── admin.html (NEEDS MAJOR UPDATE)
├── service-availability.html (faculty-facing)
└── moonlighting pages (don't touch)
```

### 5. IMPLEMENTATION PLAN (One Pass)

**Step 1:** Update admin_service.py
- Fix heatmap endpoint logic
- Fix week generation to preserve historic data
- Ensure academic year calendar logic

**Step 2:** Create new admin.html
- Single "Manage Faculty" section
- Display all new fields
- Remove provider section entirely
- 7 clear tabs as specified

**Step 3:** Test complete workflow
- Add faculty member with service commitments
- Generate weeks for academic year
- Import historic data
- View heatmaps (both years)
- Verify no data loss

**Step 4:** Documentation
- Update README with clear architecture
- Document CSV import formats
- Explain academic year model

### 6. CSV IMPORT FORMATS

#### Faculty Import
```csv
id,name,email,rank,clinical_effort_pct,base_points,bonus_points,active,is_admin,MICU_Weeks,APP_ICU_Weeks,Procedure_Weeks,Consult_Weeks
KE4Z,Kyle Enfield,ke4z@uvahealth.org,full,20,50,0,TRUE,TRUE,0,8,4,0
```

#### Historic Assignments Import
```csv
faculty_id,week_number,service_type,year
KE4Z,1,MICU,2025
IN2C,2,APP-ICU,2025
```

#### Historic Unavailability Import  
```csv
week_number,year,unavailable_count
1,2025,8
2,2025,5
```

## CRITICAL REMINDERS

1. **Academic Year:** July 1 to June 30 (NOT calendar year)
2. **Availability System:** Faculty request when they CAN'T work
3. **Single Faculty Table:** Provider table is ONLY for moonlighting
4. **Preserve Data:** Never delete weeks or historic_unavailable_count
5. **Two Heatmaps:** One for current year (requests), one for historic year (seed data)
