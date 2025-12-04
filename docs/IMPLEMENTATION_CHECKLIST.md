# Complete Implementation Checklist

## Files to Update

### 1. backend/routes/admin_service.py
**Issues to Fix:**
- ✅ Heatmap logic already correct (uses historic_unavailable_count when > 0)
- ❌ Week generation throws error if weeks exist (should skip existing)
- ❌ Historic assignment import doesn't calculate historic_unavailable_count
- ❌ Need endpoint to import historic unavailability directly

**Changes Needed:**
1. Modify `generate_service_weeks` to skip existing weeks instead of erroring
2. Add `/import-historic-unavailability` endpoint
3. Update `import_historic_assignments` to calculate and set historic_unavailable_count

### 2. admin.html (Complete Rewrite)
**Current State:** Mixed provider/faculty display
**Target State:** Clean 7-tab interface

**Tab Structure:**
1. Manage Faculty (faculty CRUD with new fields)
2. Moonlighting/IRPA (existing - don't touch)
3. Service Overview (current year heatmap)
4. Configure Periods (historic heatmap + generate weeks)
5. View Requests (unavailability requests table)
6. Manage Weeks (week settings editor)
7. Build Schedule (future feature placeholder)

### 3. Documentation
- ✅ SYSTEM_ARCHITECTURE.md created
- ❌ Update README.md
- ❌ Create DEPLOYMENT.md

## Implementation Order

### Phase 1: Backend Fixes (30 min)
1. Update admin_service.py with 3 fixes
2. Test endpoints via curl/Postman
3. Commit to branch

### Phase 2: Frontend Rebuild (60 min)
1. Create new admin.html from scratch
2. Implement 7 tabs with proper data display
3. Test all CRUD operations
4. Commit to branch

### Phase 3: Testing & Documentation (30 min)
1. Test complete workflow
2. Update documentation
3. Create final PR

## Testing Checklist

### Backend Tests
- [ ] GET /api/admin/faculty returns new fields
- [ ] PATCH /api/admin/faculty/{id} updates service weeks
- [ ] POST /api/admin/generate-service-weeks (doesn't delete existing)
- [ ] POST /api/admin/import-historic-assignments (sets unavailable count)
- [ ] POST /api/admin/import-historic-unavailability (direct import)
- [ ] GET /api/admin/service-weeks/heatmap?year=2025 (shows historic)
- [ ] GET /api/admin/service-weeks/heatmap?year=2026 (shows current)

### Frontend Tests
- [ ] Faculty table displays all fields correctly
- [ ] Can edit moonlighter checkbox
- [ ] Can edit service week numbers
- [ ] Heatmap displays for current year
- [ ] Historic heatmap displays for previous year
- [ ] Can generate weeks without deleting existing
- [ ] No provider/faculty duplication

### Integration Tests
- [ ] Import faculty CSV
- [ ] Generate weeks for 2026-2027
- [ ] Import historic 2025-2026 data
- [ ] View both heatmaps
- [ ] Faculty can request unavailability
- [ ] Admin sees requests

## Success Criteria

1. ✅ Single "Faculty" table (no provider confusion)
2. ✅ All new fields visible and editable
3. ✅ Heatmap works for both years
4. ✅ Week generation preserves data
5. ✅ Academic year calendar (July-June)
6. ✅ Clean 7-tab interface
7. ✅ No data loss during operations

## Rollback Plan

If issues occur:
```bash
git checkout fix/critical-issues
git branch -D fix/provider-fields-and-historic-data
```

Database backup before major operations:
```bash
cp moonlighter.db moonlighter.db.backup.$(date +%Y%m%d_%H%M%S)
```
