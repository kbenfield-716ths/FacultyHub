# Moonlighting System Fixes

## Issues Identified

### 1. Data Not Showing in Moonlighting System
**Root Cause**: Authentication mismatch between Faculty login system and moonlighting Provider system
- Faculty log in via session-based authentication (Faculty model)
- Moonlighting system expects provider_id from localStorage or URL params
- Fetch requests missing `credentials: 'same-origin'` needed for session auth

### 2. Schedule Clearing Not Working  
**Root Cause**: Admin clear endpoints lacked authentication requirements
- `/api/admin/clear_month` and `/api/admin/clear_all` endpoints had no auth
- Frontend likely not sending credentials with requests

## Fixes Applied

### signup.html Changes
1. **Added credentials to fetch requests**:
   ```javascript
   const res = await fetch(`${API_BASE}/api/signup`, {
     method: "POST",
     headers: { "Content-Type": "application/json" },
     credentials: 'same-origin',  // <-- CRITICAL FIX
     body: JSON.stringify(payload),
   });
   ```

2. **Improved user loading**:
   - Primary: Fetch current user from `/api/me` endpoint using session
   - Fallback: Check localStorage for backward compatibility
   - Proper error handling and user feedback

3. **Enhanced logging**:
   - Added console logging for debugging auth issues
   - Better error messages to user

### backend/app.py Changes

1. **Created /api/me endpoint**:
   ```python
   @app.get("/api/me")
   def get_current_user_info(
       current_user: Faculty = Depends(get_current_user),
       db: Session = Depends(get_db)
   ):
       """Get current logged-in user info."""
       return {
           "faculty_id": current_user.id,
           "faculty_name": current_user.name,
           "email": current_user.email,
           "is_admin": current_user.is_admin,
           "moonlighter": current_user.moonlighter
       }
   ```

2. **Added authentication to ALL moonlighting endpoints**:
   - `/api/signup` - Now requires login, validates user signing up for themselves
   - `/api/providers` - Requires authentication
   - `/api/admin/signups` - Requires admin role
   - `/api/admin/assignments` - Requires admin role
   - `/api/admin/providers/*` - All provider management requires admin
   - `/api/admin/clear_month` - Requires admin role
   - `/api/admin/clear_all` - Requires admin role
   - `/api/admin/run_optimizer` - Requires admin role
   - `/api/admin/signups_csv` - Requires admin role

3. **Added proper authorization checks**:
   ```python
   if not current_user.is_admin:
       raise HTTPException(403, "Admin access required")
   ```

4. **Improved /api/signup validation**:
   ```python
   # Verify the user is signing up for themselves
   if payload.provider_id != current_user.id:
       raise HTTPException(403, "You can only sign up for yourself")
   ```

## How It Works Now

### For Faculty Users:
1. Faculty logs in via session-based auth (existing system)
2. When visiting signup.html:
   - Page calls `/api/me` with credentials to get current user
   - Provider info (faculty_id, faculty_name) loaded from session
   - Calendar displays with correct user context
3. When submitting availability:
   - Fetch includes `credentials: 'same-origin'`
   - Backend validates user is logged in
   - Backend ensures user only signs up for themselves
   - Data saved to Provider table

### For Admin Users:
1. Admin logs in with is_admin=True
2. Admin endpoints verify `current_user.is_admin` 
3. All admin actions now properly authenticated:
   - View all signups
   - View assignments
   - Run optimizer
   - Clear schedules (month or all)
   - Export CSV

## Testing Checklist

- [ ] Faculty can log in and access signup.html
- [ ] Signup page displays correct faculty name
- [ ] Faculty can select dates and save moonlighting preferences
- [ ] Data persists and shows in admin view
- [ ] Admin can view all faculty signups
- [ ] Admin can run optimizer
- [ ] Admin can clear month data
- [ ] Admin can clear all data
- [ ] Non-admin cannot access admin endpoints
- [ ] Faculty cannot sign up for other faculty members

## Database Schema Notes

The system maintains two separate but related tables:
- **Faculty**: Main user table with authentication, used for service availability
- **Provider**: Moonlighting-specific table, auto-created from Faculty when they sign up

Both use the same ID (faculty computing ID like "KE4Z"), ensuring consistency.

## Backward Compatibility

The signup page still checks localStorage as fallback for any existing
workflows that might use URL parameters or local storage. However, the
primary authentication flow is now via session + `/api/me` endpoint.
