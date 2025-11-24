# Authentication System Testing Guide

## What Was Built

A complete authentication system with:
- **Session-based authentication** using secure cookies
- **Password hashing** with bcrypt
- **Login/logout flow** with user context
- **Admin role checking** for protected routes
- **Default admin user** created on startup

## Files Created/Modified

### New Files
1. `backend/auth.py` - Core authentication logic
2. `backend/routes/auth.py` - Auth API endpoints
3. `login.html` - Login page UI
4. `backend/scripts/init_test_users.py` - Test user creation script

### Modified Files
1. `requirements.txt` - Added passlib, python-jose, python-multipart
2. `backend/app.py` - Added auth router, creates default admin on startup
3. `backend/routes/admin_faculty.py` - Uses real auth dependencies

## Testing Instructions

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Initialize Test Users (Optional)

```bash
python backend/scripts/init_test_users.py
```

This creates:
- **ADMIN** / PCCM2025! (admin user)
- **TEST1** / PCCM2025! (regular faculty)
- **TEST2** / PCCM2025! (regular faculty)
- **TEST3** / PCCM2025! (admin faculty)

### Step 3: Start the Server

```bash
uvicorn backend.app:app --reload
```

Or if using Docker/fly.io, just deploy normally.

### Step 4: Test Login Flow

1. **Navigate to login page:**
   ```
   http://localhost:8000/login.html
   ```

2. **Test login with default admin:**
   - Faculty ID: `ADMIN`
   - Password: `PCCM2025!`

3. **Should redirect to home** (`/`) after successful login

4. **Test logout:**
   - Open browser console
   - Run: `fetch('/api/auth/logout', {method: 'POST', credentials: 'include'}).then(() => location.reload())`

### Step 5: Test API Endpoints

#### Check Auth Status
```bash
curl http://localhost:8000/api/auth/check
```

Should return:
```json
{"authenticated": false}
```

#### Login via API
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"faculty_id": "ADMIN", "password": "PCCM2025!"}' \
  -c cookies.txt
```

#### Get Current User
```bash
curl http://localhost:8000/api/auth/me \
  -b cookies.txt
```

#### Test Admin Endpoint
```bash
curl http://localhost:8000/api/admin/faculty \
  -b cookies.txt
```

#### Logout
```bash
curl -X POST http://localhost:8000/api/auth/logout \
  -b cookies.txt \
  -c cookies.txt
```

## Authentication Flow

### How It Works

1. **User visits login page** (`/login.html`)
2. **Enters faculty ID and password**
3. **Frontend sends POST to** `/api/auth/login`
4. **Backend validates credentials:**
   - Checks Faculty table for matching ID
   - Verifies password with bcrypt
   - Creates session token
5. **Sets httponly cookie** with session token
6. **Frontend redirects** to home page
7. **Subsequent requests** include session cookie
8. **Backend validates** session on each request

### Session Management

- **Storage:** In-memory dictionary (for development)
- **Duration:** 24 hours
- **Cookie:** httponly, samesite=lax
- **Token:** Secure random 32-byte URL-safe string

### Protected Routes

All routes in `/api/admin/` require authentication.

To protect a route:
```python
from backend.auth import require_admin, get_current_user

@router.get("/protected")
def protected_route(user: Faculty = Depends(get_current_user)):
    return {"message": f"Hello {user.name}"}

@router.get("/admin-only")
def admin_route(admin: Faculty = Depends(require_admin)):
    return {"message": f"Admin {admin.name} has access"}
```

## Frontend Integration

### Check if User is Logged In

```javascript
async function checkAuth() {
  const response = await fetch('/api/auth/check', {
    credentials: 'include'
  });
  const data = await response.json();
  
  if (data.authenticated) {
    console.log(`Logged in as: ${data.faculty_name}`);
    console.log(`Is admin: ${data.is_admin}`);
  } else {
    console.log('Not logged in');
  }
}
```

### Get Current User Info

```javascript
async function getCurrentUser() {
  const response = await fetch('/api/auth/me', {
    credentials: 'include'
  });
  
  if (response.ok) {
    const user = await response.json();
    return user;
  } else {
    // Not logged in or session expired
    return null;
  }
}
```

### Logout

```javascript
async function logout() {
  await fetch('/api/auth/logout', {
    method: 'POST',
    credentials: 'include'
  });
  
  // Redirect to login or home
  window.location.href = '/login.html';
}
```

## Common Issues

### Issue: Login succeeds but still shows as not authenticated

**Solution:** Make sure you're including `credentials: 'include'` in all fetch calls.

### Issue: Session expires too quickly

**Solution:** Increase session duration in `backend/auth.py`:
```python
if datetime.utcnow() - session["created_at"] > timedelta(hours=72):  # 3 days
```

### Issue: Can't create admin users

**Solution:** Only admins can create users. Login as ADMIN first, then use the admin panel.

### Issue: Import errors for passlib or python-jose

**Solution:** Reinstall requirements:
```bash
pip install --upgrade -r requirements.txt
```

## Next Steps

Now that authentication works, you can:

1. **Add user context to all pages** - Show logged-in user's name
2. **Protect admin routes on frontend** - Hide admin buttons for non-admins
3. **Build inpatient scheduling UI** - Let faculty select vacation weeks
4. **Add "remember me" functionality** - Extend session duration
5. **Implement password change flow** - Force users to change default password

## Production Considerations

### Before deploying to production:

1. **Use Redis for session storage** instead of in-memory dict
2. **Add rate limiting** to login endpoint
3. **Enable HTTPS only** for cookies
4. **Add password complexity requirements**
5. **Implement password reset via email**
6. **Add session cleanup job** to remove expired sessions
7. **Consider adding 2FA** for admin users

## Database Schema

The Faculty table includes:
- `id` - UVA computing ID (primary key)
- `name` - Full name
- `email` - Email address
- `password_hash` - Bcrypt hashed password
- `password_changed` - Boolean, false if using default password
- `is_admin` - Boolean, true for admin users
- `active` - Boolean, false for deactivated users
- `rank` - Faculty rank (assistant, associate, full)
- `clinical_effort_pct` - Clinical effort percentage
- `base_points` - Point allocation for scheduling
- `bonus_points` - Bonus points earned

## API Endpoints

### Auth Endpoints
- `POST /api/auth/login` - Login with faculty_id and password
- `POST /api/auth/logout` - Logout and clear session
- `GET /api/auth/me` - Get current user info
- `GET /api/auth/check` - Check if authenticated (no error if not)
- `POST /api/auth/change-password` - Change password for current user

### Admin Endpoints (Require Admin Auth)
- `GET /api/admin/faculty` - List all faculty
- `GET /api/admin/faculty/{id}` - Get faculty by ID
- `POST /api/admin/faculty` - Create new faculty
- `PATCH /api/admin/faculty/{id}` - Update faculty
- `DELETE /api/admin/faculty/{id}` - Soft delete faculty
- `POST /api/admin/faculty/{id}/reset-password` - Reset faculty password
- `POST /api/admin/faculty/{id}/toggle-admin` - Toggle admin status
- `GET /api/admin/faculty/stats/summary` - Get faculty statistics
