# STEP-BY-STEP IMPLEMENTATION INSTRUCTIONS

## Overview
This document provides exact code changes to fix all issues in one pass.
Apply these changes in order, test after each section.

## Part 1: Backend Fixes (15 minutes)

### File: backend/routes/admin_service.py

#### Change 1: Fix Week Generation (Line 443)
**Find this code (around line 443):**
```python
    # Check if weeks already exist for this year
    existing = db.query(ServiceWeek).filter(ServiceWeek.year == request.year).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Weeks already exist for {request.year}. Clear them first."
        )
```

**Replace with:**
```python
    # Check which weeks already exist and skip them (preserve historic data)
    existing_weeks = {w.week_number for w in db.query(ServiceWeek).filter(ServiceWeek.year == request.year).all()}
    weeks_skipped = 0
```

#### Change 2: Skip Existing Weeks in Loop (Line 524)
**Find this line (around line 524):**
```python
    for week_num in range(1, 53):
        end_date = current_date + timedelta(days=6)
```

**Add these lines RIGHT AFTER the `for` statement:**
```python
    for week_num in range(1, 53):
        # Skip if week already exists (preserve data)
        if week_num in existing_weeks:
            weeks_skipped += 1
            current_date = current_date + timedelta(days=7)
            continue
            
        end_date = current_date + timedelta(days=6)
```

#### Change 3: Update Return Statement (Line 559)
**Find this return statement (around line 559):**
```python
    return {
        "success": True,
        "weeks_created": len(weeks_created),
        "year": request.year,
        "start_date": request.start_date,
        "end_date": weeks_created[-1].end_date.isoformat()
    }
```

**Replace with:**
```python
    return {
        "success": True,
        "weeks_created": len(weeks_created),
        "weeks_skipped": weeks_skipped,
        "year": request.year,
        "start_date": request.start_date,
        "end_date": weeks_created[-1].end_date.isoformat() if weeks_created else None
    }
```

#### Change 4: Add Historic Unavailability Calculation (Line 235)
**Find the end of the `import_historic_assignments` function (around line 235), RIGHT BEFORE `db.commit()`:**

```python
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                continue
        
        db.commit()  # <-- ADD CODE BEFORE THIS LINE
```

**Add this code BEFORE `db.commit()`:**
```python
        # Calculate historic_unavailable_count for each week based on assignments
        week_faculty_map = {}
        for assignment in db.query(ServiceWeekAssignment).filter(
            ServiceWeekAssignment.imported == True,
            ServiceWeekAssignment.week_id.like(f"%-{year}")  # Only this year
        ).all():
            if assignment.week_id not in week_faculty_map:
                week_faculty_map[assignment.week_id] = set()
            week_faculty_map[assignment.week_id].add(assignment.faculty_id)
        
        # Update historic_unavailable_count  
        total_active = db.query(func.count(Faculty.id)).filter(Faculty.active == True).scalar() or 0
        weeks_updated_count = 0
        
        for week_id, faculty_set in week_faculty_map.items():
            week = db.query(ServiceWeek).filter_by(id=week_id).first()
            if week and total_active > 0:
                faculty_working = len(faculty_set)
                week.historic_unavailable_count = max(0, total_active - faculty_working)
                weeks_updated_count += 1
        
        db.commit()
```

**Then update the return statement to include:**
```python
        return {
            "success": True,
            "assignments_created": assignments_created,
            "weeks_marked_premium": weeks_marked_premium,
            "weeks_updated": weeks_updated_count,  # ADD THIS LINE
            "errors": errors if errors else None,
            "message": f"Imported {assignments_created} assignments" + 
                      (f" with {len(errors)} errors" if errors else "")
        }
```

#### Change 5: Add New Endpoint (After Line 257)
**Find the end of `import_historic_assignments` function (around line 257).**

**Add this ENTIRE new function AFTER it:**
```python

@router.post("/import-historic-unavailability")
async def import_historic_unavailability(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Faculty = Depends(require_admin)
):
    """
    Import historic unavailability counts directly from CSV.
    
    CSV Format:
    week_number,year,unavailable_count
    1,2025,8
    2,2025,5
    
    This directly sets the historic_unavailable_count field for display in heatmaps.
    """
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        contents = await file.read()
        csv_data = io.StringIO(contents.decode('utf-8'))
        csv_reader = csv.DictReader(csv_data)
        
        required_columns = {'week_number', 'year', 'unavailable_count'}
        if not required_columns.issubset(csv_reader.fieldnames or []):
            raise HTTPException(
                status_code=400,
                detail=f"CSV must have columns: {', '.join(required_columns)}"
            )
        
        weeks_updated = 0
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                week_number = int(row['week_number'])
                year = int(row['year'])
                unavailable_count = int(row['unavailable_count'])
                
                if week_number < 1 or week_number > 52:
                    errors.append(f"Row {row_num}: Invalid week number {week_number}")
                    continue
                
                week_id = f"W{week_number:02d}-{year}"
                week = db.query(ServiceWeek).filter_by(id=week_id).first()
                
                if not week:
                    errors.append(f"Row {row_num}: Week {week_number} for year {year} not found")
                    continue
                
                week.historic_unavailable_count = unavailable_count
                weeks_updated += 1
                
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                continue
        
        db.commit()
        
        return {
            "success": True,
            "weeks_updated": weeks_updated,
            "errors": errors if errors else None,
            "message": f"Updated {weeks_updated} weeks" + 
                      (f" with {len(errors)} errors" if errors else "")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing CSV: {str(e)}")
```

### Save and Test Backend
```bash
# Restart server
uvicorn backend.app:app --host 0.0.0.0 --port 8000

# Test API
curl http://localhost:8000/api/admin/faculty | head -50
```

## Part 2: Frontend Admin Interface

The new admin.html will have:
1. Single "Manage Faculty" tab (no provider duplication)
2. Display all service week fields  
3. Moonlighter checkbox
4. 7 clear tabs as specified

Frontend implementation will be tackled in a separate focused session after backend is working.
