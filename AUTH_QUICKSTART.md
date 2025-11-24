# Authentication System - Quick Start

## 🚀 What's New

Complete authentication system is now live! Faculty can log in, and admin users can manage the system.

## 📋 Quick Setup

### 1. Update Dependencies

```bash
pip install -r requirements.txt
```

**New dependencies added:**
- `passlib[bcrypt]` - Secure password hashing
- `python-jose[cryptography]` - JWT/session tokens
- `python-multipart` - Form data handling

### 2. Start the Server

```bash
# Local development
uvicorn backend.app:app --reload

# Or with fly.io
fly deploy
```

### 3. Login with Default Admin

**Default admin credentials** (created automatically on first startup):
- **Faculty ID:** `ADMIN`
- **Password:** `PCCM2025!`

**Login page:** `http://localhost:8000/login.html` or `https://your-app.fly.dev/login.html`

## 🧪 Testing

### Option 1: Use Default Admin
The app automatically creates an ADMIN user on first startup. Just login with ADMIN / PCCM2025!

### Option 2: Create Test Users
```bash
python backend/scripts/init_test_users.py
```

This creates:
- `ADMIN` - Administrator (admin)
- `TEST1` - Dr. Jane Smith (regular)
- `TEST2` - Dr. John Doe (regular)  
- `TEST3` - Dr. Sarah Johnson (admin)

All use password: `PCCM2025!`

### Option 3: Add Real Faculty via Admin Panel
1. Login as ADMIN
2. Navigate to admin panel
3. Add real faculty with UVA computing IDs

## 🔒 How Authentication Works

1. **User visits** `/login.html`
2. **Enters credentials** (Faculty ID + Password)
3. **Server validates** and creates session
4. **Session cookie set** (24-hour expiry)
5. **User redirected** to home page
6. **Protected routes** check session cookie

## 📚 Documentation

**Full testing guide:** See [TEST_AUTH.md](./TEST_AUTH.md)

**Key features:**
- ✅ Session-based authentication
- ✅ Bcrypt password hashing
- ✅ Admin role checking
- ✅ Auto-created default admin
- ✅ Password change flow (coming soon)
- ✅ 24-hour session duration

## 🛠️ API Endpoints

### Public Endpoints
- `POST /api/auth/login` - Login
- `POST /api/auth/logout` - Logout
- `GET /api/auth/check` - Check auth status

### Protected Endpoints (Require Login)
- `GET /api/auth/me` - Get current user

### Admin Endpoints (Require Admin)
- `GET /api/admin/faculty` - List all faculty
- `POST /api/admin/faculty` - Create faculty
- `PATCH /api/admin/faculty/{id}` - Update faculty
- `DELETE /api/admin/faculty/{id}` - Delete faculty
- More in [TEST_AUTH.md](./TEST_AUTH.md)

## 🔧 Next Steps After Testing Login

Once you verify login works:

1. **Update index.html** - Show logged-in user, add logout button
2. **Protect admin panel** - Only show to admins
3. **Build inpatient scheduling** - Faculty select vacation weeks
4. **Add user dropdown** - Show who's logged in everywhere

## 🐛 Troubleshooting

### Database Issues
```bash
# Delete database and start fresh
rm moonlighter.db
# Restart server - new db with ADMIN user created automatically
```

### Import Errors
```bash
pip install --upgrade -r requirements.txt
```

### Session Not Working
Make sure frontend uses `credentials: 'include'` in fetch calls:
```javascript
fetch('/api/auth/check', { credentials: 'include' })
```

## 📞 Need Help?

Check the detailed testing guide in `TEST_AUTH.md` for:
- API testing with curl
- Frontend integration examples
- Common issues and solutions
- Production deployment tips
