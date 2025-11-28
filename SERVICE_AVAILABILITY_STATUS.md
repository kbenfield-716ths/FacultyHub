# Service Availability - Admin Panel Integration

## Current Status

✅ **Backend API Complete**
- Enhanced admin service routes with special week configuration
- Week editing endpoint (`PUT /api/admin/service-weeks/{week_id}`)
- Special weeks generation with flexible configuration
- All endpoints functional and tested

✅ **Standalone Config Page Created** 
- `admin-config.html` - Full featured configuration interface
- Special week presets (Christmas, Thanksgiving, Conferences)
- Inline editing of weeks
- 3-step workflow for configuration

✅ **Dashboard Route Added**
- `dashboard.html` created with redirect to index.html

## Current Files

### Working Admin Panels:
1. **Admin.html** (root) - Old comprehensive panel with:
   - Faculty management
   - Moonlighting schedule management
   - Yearly calendar build (unavailable weeks)
   - Uses local API (`https://moonlighter-web.fly.dev`)
   
2. **backend/static/admin.html** - New admin panel with:
   - Overview tab (statistics)
   - Faculty tab (add/manage)
   - Moonlighting tab (summary)
   - Service Availability tab (basic generation)
   - Proper authentication integration
   - Uses local API (`/api/...`)

3. **admin-config.html** - Standalone service configuration with:
   - Special week configuration form
   - Preset templates
   - Generate 52 weeks with special weeks
   - Inline week editing
   - No authentication (standalone)

## The 401 Errors

The 401 errors you're seeing are normal - they occur when:
1. User visits Admin.html before logging in
2. JavaScript tries to call `/api/auth/me` to check auth status
3. Server correctly returns 401 (not authenticated)
4. User then logs in successfully
5. Subsequent calls work fine

**This is expected behavior - not a bug.**

## Next Steps - Integration Options

### Option 1: Keep Separate Admin Panels (Easiest)
Leave Admin.html as-is for moonlighting, add link to admin-config.html for service availability:

```html
<!-- In Admin.html, add to navigation -->
<button onclick="window.location.href='/admin-config.html'">
  Configure Service Availability
</button>
```

### Option 2: Merge Into One Panel (Recommended)
Integrate the service availability configuration into the comprehensive admin panel at `backend/static/admin.html`:

**Add a new tab:**
1. Add tab button: `<button class="tab-btn" onclick="showTab('service-config')">⚙️ Service Config</button>`
2. Copy service configuration HTML from admin-config.html
3. Copy JavaScript functions for special weeks
4. Style to match existing design

**Benefits:**
- Single admin interface
- Consistent authentication
- Better user experience
- Easier to maintain

### Option 3: Update Old Admin.html
Update the root Admin.html to use new backend API and add service configuration tab.

## Recommended Implementation

**I recommend Option 2** - Merge into backend/static/admin.html because:
1. Already has proper auth integration
2. Clean 4-tab design ready for expansion
3. Consistent API usage
4. Better organized codebase

### Quick Integration Steps:

1. **Add Service Config Tab** to `backend/static/admin.html`
2. **Copy configuration UI** from `admin-config.html`
3. **Update Service Availability tab** to include:
   - Step 1: Configure Special Weeks (with presets)
   - Step 2: Generate 52 Weeks
   - Step 3: Review and Edit (inline editing)
4. **Test workflow:**
   - Login as ADMIN
   - Click Service Config tab
   - Add special weeks
   - Generate schedule
   - Edit individual weeks

## Files to Update

```
backend/static/admin.html (main admin panel)
├── Add service-config tab button
├── Add special weeks configuration UI
├── Add preset buttons (Christmas, Thanksgiving, etc.)
├── Add inline editing for weeks table
└── Update generateWeeks() to send special_weeks array

Admin.html (root - legacy)
├── Keep for moonlighting management
└── Add link to new admin panel if desired
```

## API Endpoints Available

```javascript
// Generate weeks with special configuration
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

// Update individual week
PUT /api/admin/service-weeks/{week_id}
{
  "label": "Week 12 - Holiday Break",
  "point_cost_off": 20,
  "point_reward_work": 25
}

// Get weeks for year
GET /api/admin/service-weeks?year=2026

// Clear weeks
DELETE /api/admin/service-weeks?year=2026
```

## Testing

1. Restart server: `python -m uvicorn backend.app:app --reload`
2. Login: `http://localhost:8000` → Login as ADMIN / PCCM2025!
3. Admin Panel: `http://localhost:8000/admin.html`
4. Config Page: `http://localhost:8000/admin-config.html`

## Summary

You now have:
- ✅ All backend APIs working
- ✅ Standalone configuration interface
- ✅ Authentication system working correctly
- ✅ Old admin panel preserved
- ✅ New admin panel with proper auth

**The 401 errors are normal and expected** - they happen before login and don't affect functionality.

**Next:** Choose integration option and merge service configuration into main admin panel.
