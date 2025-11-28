# Unified Admin Panel - Setup Instructions

## What I've Created

I've created **ONE comprehensive admin panel** (`admin.html`) with **6 tabs** that combines ALL functionality:

### The 6 Tabs:
1. **👥 Manage Providers** - Add/edit/delete faculty
2. **🌙 Moonlighting/IRPA** - Manage moonlighting schedules and optimizer
3. **📊 Service Overview** - View service availability system status
4. **⚙️ Configure Periods** - Define special periods and generate 52 weeks
5. **📈 View Requests** - See all faculty service availability requests
6. **📅 Manage Weeks** - Edit the 52-week schedule inline

## How to Install

The complete unified admin panel file is ready at `/tmp/unified_admin.html` on the Claude computer.

### Option 1: Copy from local file (Recommended)

```bash
cd ~/Library/Mobile\ Documents/com~apple~CloudDocs/FacultyScheduling/moonlighter-web
git checkout unified-admin
git pull origin unified-admin

# The unified admin HTML is in /tmp/unified_admin.html - copy it:
# (I can't directly write it to GitHub due to size limits, but you can copy it locally)
```

### Option 2: Direct download

Visit: https://github.com/kbenfield-716ths/moonlighter-web/tree/unified-admin

The placeholder is there - you'll need to replace it with the full content from `/tmp/unified_admin.html`

## Features

✅ **Single file** - No more conflicts between Admin.html and admin.html
✅ **6 comprehensive tabs** - All functionality in one place
✅ **Clean design** - Modern UI with gradient buttons
✅ **Tab navigation** - Easy switching between sections
✅ **Auto-loading** - Data loads automatically on page load and tab switches
✅ **Local API** - Uses `const API_BASE = ""` for local development
✅ **Authentication** - Checks admin privileges on load
✅ **Inline editing** - Click cells to edit weeks directly
✅ **Complete moonlighting** - Full calendar, optimizer, CSV download
✅ **Service availability** - Configure periods, manage weeks, view requests

## What's Different

- **No more file conflicts!** Just one admin.html (lowercase)
- **Tabbed interface** instead of separate pages
- **All in one place** - Providers, moonlighting, AND service availability
- **Better UX** - Navigation is clear and intuitive
- **Updated API calls** - Uses local API instead of fly.dev

## Next Steps

1. Switch to the unified-admin branch
2. Copy the complete file from `/tmp/unified_admin.html` to `admin.html`
3. Commit and push
4. Test locally:
   ```bash
   python -m uvicorn backend.app:app --reload
   ```
5. Visit: http://localhost:8000/admin.html
6. Login with admin credentials

## Alternative: I can paste the content

If you'd like, I can paste the complete 1,183-line HTML file content in a follow-up message for you to copy directly!

Let me know how you'd like to proceed.
