# Faculty Management in Admin Panel

## Overview
The admin panel now has comprehensive faculty management with the ability to:
- View all faculty with their roles, ranks, and admin status
- Edit faculty details (name, email, rank, clinical effort, points)
- Toggle admin status
- Reset passwords
- Deactivate faculty members
- View both Provider (moonlighting) and Faculty (authentication/scheduling) records

## Available Endpoints

### GET /api/admin/faculty
Get all faculty members
- Query param: `active_only=true` to filter only active faculty
- Returns array of faculty with all fields

### GET /api/admin/faculty/{faculty_id}
Get specific faculty member details

### POST /api/admin/faculty
Create new faculty member
- Requires: id, name, email, rank, clinical_effort_pct, base_points
- Optional: bonus_points, active, is_admin
- Default password: PCCM2025!

### PATCH /api/admin/faculty/{faculty_id}
Update existing faculty (partial update)
- All fields optional
- Validates rank (assistant/associate/full)
- Checks email uniqueness

### DELETE /api/admin/faculty/{faculty_id}
Soft delete (sets active=false)

### POST /api/admin/faculty/{faculty_id}/reset-password
Reset faculty password
- Body: {"new_password": "..."}
- Minimum 8 characters

### POST /api/admin/faculty/{faculty_id}/toggle-admin
Toggle admin privileges on/off

### GET /api/admin/faculty/stats/summary
Get faculty statistics (counts by rank, active, admins)

## UI Implementation Notes

The admin panel should have a tab for "Faculty Management" that shows:

1. **Faculty Table** with columns:
   - Computing ID
   - Name  
   - Email
   - Rank (assistant/associate/full)
   - Clinical Effort %
   - Base Points
   - Bonus Points
   - Active (Yes/No)
   - Admin (Yes/No badge)
   - Actions (Edit, Toggle Admin, Reset Password, Deactivate)

2. **Edit Modal/Form** with fields:
   - Name (text)
   - Email (email)
   - Rank (dropdown: assistant, associate, full)
   - Clinical Effort % (number, 0-100)
   - Base Points (number)
   - Bonus Points (number)
   - Active checkbox
   - Admin checkbox

3. **Action Buttons**:
   - **Edit**: Opens modal with current values, saves with PATCH
   - **Toggle Admin**: Quick toggle with confirmation
   - **Reset Password**: Prompts for new password
   - **Deactivate**: Soft deletes (confirmation required)

## Integration with Providers

The system maintains TWO tables:
- **providers**: For moonlighting shift management (legacy)
- **faculty**: For authentication and service scheduling (new)

When creating faculty:
1. Create Faculty record (auth + scheduling)
2. Optionally create Provider record (moonlighting)

The migration script (`migrate_providers_to_faculty.py`) syncs these.
