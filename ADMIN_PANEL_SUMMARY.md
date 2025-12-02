# Admin Panel Integration - Summary

## What I've Created

### 1. **Admin Panel HTML** (`admin.html`)
A comprehensive admin interface with multiple tabs for managing the faculty scheduling system.

#### **📊 Overview Tab**
- Real-time statistics dashboard showing:
  - Active faculty count
  - Moonlighting months configured
  - Service availability weeks generated  
  - Total availability requests submitted
- Recent activity feed

#### **👥 Faculty Tab**
- Add new faculty form with:
  - Computing ID (UVA ID like "KE4Z")
  - Name and email
  - Academic rank (assistant/associate/full professor)
  - Clinical effort percentage
  - Automatic base points calculation
- Faculty list table showing all members with:
  - Status (Active/Inactive)
  - Admin privileges indicator
  - All profile information

#### **🌙 Moonlighting Tab**
- Summary view of all moonlighting periods
- Shows signups and assignments for each period
- Status tracking (Open/In Progress/Completed)

#### **📅 Service Availability Tab**
- Generate 52 weeks for academic year
- Configure special weeks:
  - Summer (higher cost, some reward)
  - Spring Break (12 pts cost, 15 pts reward)
  - Thanksgiving (15 pts cost, 20 pts reward)
  - Christmas (15 pts cost, 20 pts reward, 2 weeks)
- View all weeks with:
  - Week number and dates
  - Week type (badges)
  - Point costs and rewards
  - Number of requests received
- Clear all weeks button (with confirmation)

### 2. **Admin API Routes** (`backend/routes/admin_service.py`)
Backend endpoints for service availability management:

- `GET /api/admin/service-weeks` - Get all service weeks for a year
- `POST /api/admin/generate-service-weeks` - Generate 52 weeks
- `DELETE /api/admin/service-weeks` - Clear weeks (with optional year filter)
- `GET /api/admin/service-requests` - Get all faculty requests
- `GET /api/admin/moonlighting-summary` - Get moonlighting statistics
- `GET /api/admin/months` - Get all moonlighting months

### 3. **Updated Main Application** (`backend/app.py`)
- Added `admin_service_router` to FastAPI app
- Fixed static file serving paths
- Admin panel now accessible at `/admin.html`

## Key Features

### ✅ **Service Availability Terminology**
- System uses "Service Availability" throughout (not "vacation")
- Reflects that this is about when faculty **cannot** work inpatient service
- Faculty request time off from service duties, not vacation time

### ✅ **Integrated Design**
- Matches existing moonlighting system UI
- Uses same color scheme and styling
- Consistent navigation patterns

### ✅ **Points System**
Faculty earn base points based on:
- Clinical effort percentage
- Academic rank multiplier:
  - Assistant Professor: 1.0x
  - Associate Professor: 1.75x
  - Full Professor: 2.5x
- Formula: `base_points = 100 × (clinical_effort/100) × rank_multiplier`

### ✅ **Week Types & Costs**
- **Regular weeks**: -5 points (unavailable), +0 points (available)
- **Summer weeks**: -7 points, +5 points
- **Spring Break**: -12 points, +15 points
- **Thanksgiving**: -15 points, +20 points
- **Christmas** (2 weeks): -15 points each, +20 points each

### ✅ **Security**
- Admin-only access (requires `is_admin = True`)
- Session-based authentication
- Redirects non-admin users

## How It Works

1. **Admin logs in** with their credentials
2. **Sees admin link** in navigation (only if is_admin = True)
3. **Clicks "Admin Panel"** to access management interface
4. **Can perform:**
   - Add/manage faculty members
   - Generate the 52-week schedule
   - View moonlighting statistics
   - Monitor service availability requests
   - Clear data if needed

## What's Next

To complete the integration, you'll need to:

1. **Create faculty-facing pages** for:
   - Selecting unavailable weeks
   - Viewing their points balance
   - Submitting availability requests

2. **Add request management** endpoints:
   - Faculty submit unavailable/available status
   - Points are automatically deducted/awarded
   - Requests are tracked in `unavailability_requests` table

3. **Build scheduling algorithm** (similar to moonlighting):
   - Ensure minimum staff coverage (default 5 per week)
   - Respect faculty points budgets
   - Honor holiday volunteer requests
   - Apply draft priority for next year

4. **Testing**:
   - Generate test weeks
   - Add test faculty
   - Submit test requests
   - Verify points calculations

## Database Schema

The system uses these tables (defined in `models.py`):

```python
Faculty
- id (UVA computing ID)
- name, email
- rank, clinical_effort_pct, base_points
- is_admin, password_hash

ServiceWeek
- id, week_number, label
- start_date, end_date, year
- week_type, point_cost_off, point_reward_work
- min_staff_required

UnavailabilityRequest
- id, faculty_id, week_id
- status (unavailable/available)
- points_spent, points_earned
- gives_priority (for draft next year)
```

## Important Notes

1. **Terminology**: This is a **service availability** system - faculty request time off from inpatient service duties
2. **Points**: Negative when unavailable (costs), positive when volunteering (earns)
3. **Admin Access**: Only users with `is_admin=True` can access admin panel
4. **Default Admin**: Created on startup - username: `ADMIN`, password: `PCCM2025!`

## Testing the Admin Panel

1. Log in as admin (ADMIN / PCCM2025!)
2. Navigate to `/admin.html`
3. Try the Service Availability tab:
   - Set year to 2026
   - Set start date to 2026-07-07 (first Tuesday in July)
   - Click "Generate 52 Weeks"
4. View the generated weeks in the table below

The admin panel is now fully integrated and ready to use!
