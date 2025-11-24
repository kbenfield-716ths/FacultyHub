# ✅ Authentication System - Testing Checklist

Use this checklist to verify the authentication system is working correctly.

## 📦 Pre-Deployment Checklist

- [ ] Update requirements.txt is committed
- [ ] New files committed:
  - [ ] `backend/auth.py`
  - [ ] `backend/routes/auth.py`
  - [ ] `login.html`
  - [ ] `backend/scripts/init_test_users.py`
- [ ] Modified files committed:
  - [ ] `backend/app.py`
  - [ ] `backend/routes/admin_faculty.py`
  - [ ] `requirements.txt`

## 🚀 Deployment Steps

### Local Testing

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   - [ ] No import errors
   - [ ] passlib[bcrypt] installed
   - [ ] python-jose installed

2. **Start server:**
   ```bash
   uvicorn backend.app:app --reload
   ```
   - [ ] Server starts without errors
   - [ ] Console shows: "Created default admin user: ADMIN / PCCM2025!"

3. **Test database:**
   ```bash
   python backend/scripts/init_test_users.py
   ```
   - [ ] Test users created successfully
   - [ ] No database errors

### Login Flow Testing

4. **Access login page:**
   - [ ] Navigate to `http://localhost:8000/login.html`
   - [ ] Page loads with form
   - [ ] No console errors

5. **Test invalid login:**
   - [ ] Try faculty ID: `WRONG` password: `WRONG`
   - [ ] Should show error: "Invalid faculty ID or password"

6. **Test valid admin login:**
   - [ ] Faculty ID: `ADMIN`
   - [ ] Password: `PCCM2025!`
   - [ ] Should show "Welcome, Administrator!"
   - [ ] Should redirect to home page
   - [ ] Should set session cookie

7. **Verify session:**
   ```bash
   curl http://localhost:8000/api/auth/check --cookie-jar cookies.txt
   ```
   - [ ] Returns `{"authenticated": true, "faculty_id": "ADMIN", ...}`

8. **Test current user endpoint:**
   ```bash
   curl http://localhost:8000/api/auth/me --cookie cookies.txt
   ```
   - [ ] Returns user details
   - [ ] Shows is_admin: true

### Admin Functionality Testing

9. **Test admin faculty list:**
   ```bash
   curl http://localhost:8000/api/admin/faculty --cookie cookies.txt
   ```
   - [ ] Returns list of faculty
   - [ ] Includes ADMIN and test users

10. **Test create faculty (as admin):**
    ```bash
    curl -X POST http://localhost:8000/api/admin/faculty \
      --cookie cookies.txt \
      -H "Content-Type: application/json" \
      -d '{
        "id": "NEWUSER",
        "name": "New User",
        "email": "new@example.com",
        "rank": "assistant",
        "clinical_effort_pct": 80,
        "base_points": 100
      }'
    ```
    - [ ] Returns 201 Created
    - [ ] Faculty appears in list

11. **Test without authentication:**
    ```bash
    curl http://localhost:8000/api/admin/faculty
    ```
    - [ ] Returns 401 Unauthorized
    - [ ] Error message about authentication

### Logout Testing

12. **Test logout:**
    ```bash
    curl -X POST http://localhost:8000/api/auth/logout \
      --cookie cookies.txt \
      --cookie-jar cookies.txt
    ```
    - [ ] Returns success message
    - [ ] Session cookie cleared

13. **Verify logged out:**
    ```bash
    curl http://localhost:8000/api/auth/check --cookie cookies.txt
    ```
    - [ ] Returns `{"authenticated": false}`

### Frontend Integration Testing

14. **Test browser login:**
    - [ ] Open browser to `/login.html`
    - [ ] Open dev console
    - [ ] Login as ADMIN
    - [ ] Check Application > Cookies > session_token exists
    - [ ] Redirects to home page

15. **Test auth check in console:**
    ```javascript
    fetch('/api/auth/check', {credentials: 'include'})
      .then(r => r.json())
      .then(console.log)
    ```
    - [ ] Shows authenticated: true

16. **Test logout in browser:**
    ```javascript
    fetch('/api/auth/logout', {method: 'POST', credentials: 'include'})
      .then(() => location.reload())
    ```
    - [ ] Session cleared
    - [ ] Check shows authenticated: false

## 🌐 Production Deployment (Fly.io)

17. **Deploy to fly.io:**
    ```bash
    fly deploy
    ```
    - [ ] Deployment succeeds
    - [ ] No build errors

18. **Test production login:**
    - [ ] Navigate to `https://your-app.fly.dev/login.html`
    - [ ] Login as ADMIN / PCCM2025!
    - [ ] Redirects successfully

19. **Verify production endpoints:**
    ```bash
    curl https://your-app.fly.dev/api/auth/check
    ```
    - [ ] Returns response (not 500 error)

## 🎯 Final Verification

20. **Security checks:**
    - [ ] Session cookie is httponly
    - [ ] Password is hashed in database (not plain text)
    - [ ] Admin routes require authentication
    - [ ] Non-admin users can't access admin endpoints

21. **User experience:**
    - [ ] Login form is user-friendly
    - [ ] Error messages are clear
    - [ ] Redirect after login works
    - [ ] Session persists across page reloads

## ✨ Success Criteria

**All checks passed?** Your authentication system is ready to go!

**Next steps:**
1. ✅ Mark this task complete
2. 🎨 Add user context to all pages
3. 🔒 Build the inpatient scheduling UI
4. 👥 Add real faculty members

## 📝 Notes

**Date tested:** _______________

**Tested by:** _______________

**Issues found:**
- 
- 
- 

**Resolved:**
- 
- 
- 

---

**🎉 Once everything works, you're ready to move forward with the inpatient scheduling features!**
