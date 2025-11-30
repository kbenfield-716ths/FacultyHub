# Quick Start Guide: Admin Enhancements

This guide will help you quickly set up and start using the new admin features.

## Prerequisites

- Admin account created and logged in
- Faculty members added to the system
- Basic understanding of the service availability system

## Step-by-Step Setup

### Step 1: Generate the 52-Week Schedule

1. Navigate to `admin-config-enhanced.html` (or open from admin panel)
2. Click the **"Configure Weeks"** tab
3. Select academic year: `2026-2027`
4. Set start date: `2026-07-07` (first Tuesday of July)
5. **Optional:** Configure special periods:
   - Christmas: `2026-12-22`
   - Thanksgiving: `2026-11-26`
   - Spring Break: `2027-03-15`
   - Conferences as needed
6. Click **"Generate 52 Weeks"**
7. Confirm success message

### Step 2: Import Historic Service Assignments

1. Stay in `admin-config-enhanced.html`
2. Click the **"Import Historic Data"** tab
3. Prepare your CSV file with format:
   ```csv
   faculty_id,week_number,service_type,year
   KE4Z,1,MICU,2026
   IN2C,2,APP-ICU,2026
   ```
   - Use the provided `sample_historic_assignments.csv` as a template
   - Valid service types: `MICU`, `APP-ICU`, `Procedures`, `Consults`

4. **Upload the CSV:**
   - Drag and drop the file onto the upload zone, OR
   - Click the upload zone to browse for your file

5. **Review preview** (shows first 10 lines)

6. Click **"Import Assignments"**

7. **Verify results:**
   - Check assignments created count
   - Check weeks marked as premium
   - Review any errors reported

### Step 3: View the Heat Map

1. Click the **"Heat Map"** tab
2. Select academic year if needed
3. **Understand the color coding:**
   - **Green** = Good staffing (3+ above minimum required)
   - **Yellow** = Tight staffing (at minimum required)
   - **Red** = Critical (below minimum required)
   - **Blue border** = Special week (holiday, conference)

4. **Review each week:**
   - Hover over weeks to see details
   - Note unavailable counts
   - Check assigned counts

### Step 4: View Faculty Assignments

1. Navigate to admin panel
2. Go to **"Manage Providers"** tab
3. **Review the Service Weeks column:**
   - MICU assignments (blue badge)
   - APP-ICU assignments (yellow badge)
   - Procedures assignments (green badge)
   - Consults assignments (pink badge)
   - Total weeks assigned

4. **Check faculty points:**
   - Base points
   - Bonus points
   - Total points (base + bonus)

## Common Tasks

### Add a New Faculty Member with Assignments

1. **Add faculty first:**
   - "Manage Providers" tab → "+ Add Faculty"
   - Fill in details, click "Save"

2. **Add their assignments:**
   - Create CSV with their assignment history
   - Import via "Import Historic Data" tab

### Mark Additional Premium Weeks

**Option 1: Import historic data**
- Any week with imported assignments becomes premium automatically

**Option 2: Manual configuration**
- During week generation, mark weeks as special periods
- These get higher point costs automatically

### Check Staffing for a Specific Week

1. Open heat map
2. Find the week number
3. Click or hover to see:
   - How many faculty unavailable
   - How many volunteers
   - How many assigned
   - Staffing status

### Regenerate Weeks for New Year

1. **Clear old weeks:**
   - Configure Weeks tab → "Clear All Weeks"
   - Confirm deletion

2. **Generate new weeks:**
   - Set new year and start date
   - Configure special periods
   - Click "Generate 52 Weeks"

3. **Import new historic data if needed**

## Sample CSV Templates

### Basic Import (4 faculty, various services)

```csv
faculty_id,week_number,service_type,year
KE4Z,1,MICU,2026
KE4Z,5,MICU,2026
IN2C,2,APP-ICU,2026
IN2C,8,APP-ICU,2026
JD3X,3,Procedures,2026
JD3X,9,Procedures,2026
AB1Y,4,Consults,2026
AB1Y,11,Consults,2026
```

### Full Year Import (One faculty)

```csv
faculty_id,week_number,service_type,year
KE4Z,1,MICU,2026
KE4Z,10,MICU,2026
KE4Z,15,Procedures,2026
KE4Z,20,APP-ICU,2026
KE4Z,25,MICU,2026
KE4Z,30,Consults,2026
KE4Z,35,MICU,2026
KE4Z,40,Procedures,2026
KE4Z,45,APP-ICU,2026
KE4Z,50,MICU,2026
```

## Troubleshooting

### "Faculty X not found" error during import

**Solution:** Add the faculty member first via "Manage Providers"

### "Week not found" error during import

**Solution:** Generate weeks first via "Configure Weeks" tab

### Heat map shows all green despite no assignments

**Cause:** Total active faculty is high relative to min required  
**Not a problem:** System is correctly showing good staffing ratio

### Import succeeds but assignments don't show in faculty table

**Solution:** Refresh the page - the faculty table should automatically update

### Premium weeks not showing higher costs after import

**Check:** 
1. Verify CSV imported successfully
2. Check week configuration - it should now show `week_type: "premium"`
3. Refresh heat map to see updates

## Tips and Best Practices

1. **Generate weeks early** - At least 3 months before academic year
2. **Import historic data first** - Before faculty submit requests
3. **Review heat map weekly** - During request period
4. **Keep CSV backups** - Of all historic imports
5. **Test with sample data** - Use `sample_historic_assignments.csv` first
6. **Check faculty IDs** - Must match exactly (case-sensitive)
7. **Verify service types** - Must be exact: MICU, APP-ICU, Procedures, Consults

## Quick Reference: URLs

- **Admin Panel:** `/admin.html`
- **Enhanced Config:** `/admin-config-enhanced.html`
- **Faculty Management:** Admin Panel → "Manage Providers" tab
- **Heat Map:** Enhanced Config → "Heat Map" tab
- **Import:** Enhanced Config → "Import Historic Data" tab
- **Configure:** Enhanced Config → "Configure Weeks" tab

## Quick Reference: Service Types

| Code | Full Name | Badge Color |
|------|-----------|-------------|
| MICU | Medical ICU | Blue |
| APP-ICU | APP ICU | Yellow |
| Procedures | Procedures | Green |
| Consults | Consults | Pink |

## Quick Reference: Week Types

| Type | Point Cost | Reward | When |
|------|-----------|---------|------|
| Regular | 5 | 0 | Default |
| Premium | 7 | 5 | Historic assignments |
| Summer | 7 | 5 | June-August |
| Holiday | 15 | 20 | Christmas, Thanksgiving |
| Conference | 10-15 | 12-20 | ATS, CHEST, SCCM |

## Need More Help?

See detailed documentation:
- `ADMIN_ENHANCEMENTS.md` - Complete feature guide
- `IMPLEMENTATION_SUMMARY.md` - Technical details
- Contact system administrator

## Next Steps

Once setup is complete:

1. ✅ Weeks generated
2. ✅ Historic data imported
3. ✅ Heat map reviewed
4. ✅ Faculty assignments verified

**You're ready to:**
- Open requests for faculty
- Monitor staffing levels
- Manage service assignments
- Generate reports

Enjoy the enhanced admin panel! 🎉
