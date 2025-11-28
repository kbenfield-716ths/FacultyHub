# Clean Branch Migration Plan

## Problem
The ischedule branch has two conflicting files that cause issues on macOS:
- `Admin.html` (capital A) - Comprehensive moonlighting admin (28,741 bytes)
- `admin.html` (lowercase a) - Simpler service-only panel (21,823 bytes)

On case-insensitive filesystems, Git can't properly handle both files.

## Solution: Create Clean Branch

### Step 1: Create New Branch `ischedule-clean`
```bash
# On your local machine
cd ~/path/to/moonlighter-web
git fetch origin
git checkout -b ischedule-clean origin/ischedule
```

### Step 2: Remove Conflicting Files
```bash
# Remove the lowercase admin.html (we'll keep the uppercase Admin.html)
git rm admin.html
git commit -m "Remove conflicting lowercase admin.html"
```

### Step 3: Rename Admin.html to admin-moonlighting.html
```bash
# This avoids any case-sensitivity issues in the future
git mv Admin.html admin-moonlighting.html
git commit -m "Rename Admin.html to admin-moonlighting.html for clarity"
```

### Step 4: Update References
Update any links that point to Admin.html:
- In index.html
- In any navigation

### Step 5: Push Clean Branch
```bash
git push origin ischedule-clean
```

### Step 6: Switch to Clean Branch
```bash
git checkout ischedule-clean
git pull origin ischedule-clean
```

## File Structure After Cleanup

```
Root Directory:
├── admin-moonlighting.html   # Comprehensive moonlighting admin (was Admin.html)
├── admin-config.html          # Service availability configuration
├── index.html                 # Main landing page
├── login.html                 # Login page
├── signup.html                # Faculty signup
├── Scheduling.html            # Moonlighter calendar
├── resources.html             # Resources page
└── backend/
    ├── app.py                 # FastAPI application
    ├── models.py              # Database models
    ├── routes/
    │   ├── auth.py            # Authentication routes
    │   ├── admin_faculty.py   # Faculty management
    │   └── admin_service.py   # Service availability
    └── static/                # (empty - no admin.html conflict)
```

## What You'll Do

1. I'll create the ischedule-clean branch with fixes
2. You run these commands:
```bash
cd ~/Library/Mobile\ Documents/com~apple~CloudDocs/FacultyScheduling/moonlighter-web
git fetch origin
git checkout ischedule-clean
git pull origin ischedule-clean
```

3. Restart your server:
```bash
python -m uvicorn backend.app:app --reload
```

4. Access:
- Moonlighting Admin: http://localhost:8000/admin-moonlighting.html
- Service Config: http://localhost:8000/admin-config.html

## Benefits

✅ No more filename conflicts
✅ Clear, descriptive names
✅ Works on all filesystems (macOS, Linux, Windows)
✅ Easy to maintain
✅ All functionality preserved

Ready to proceed?
