# Scheduling Enhancements - Feature Documentation

This document describes the new features added in the `scheduling-enhancements` branch.

## Overview

Two major features have been implemented:

1. **Enhanced Faculty Data Model** - Expanded faculty profiles with moonlighting eligibility, service week allocations, points system, and bid priority
2. **Heatmap Visualization System** - Dynamic point cost calculation based on request demand with historic data support

---

## Feature 1: Enhanced Faculty Data

### New Faculty Fields

The `Faculty` model has been expanded with the following fields:

#### Moonlighting Eligibility
- `eligible_moonlighter` (Boolean) - Toggle to indicate if faculty member is eligible for moonlighting/IRPA shifts

#### Points System
- `available_points` (Integer, default: 100) - Current point balance for service unavailability requests
- Faculty earn/spend points when requesting time off or volunteering

#### Bid Priority
- `bid_priority` (Integer, default: 0) - Priority for rolling draft system
- Higher numbers = earlier selection
- Used to give preference to faculty who worked holidays in previous years

#### Service Week Allocations
Four service domains with min/max week allocations:

1. **MICU**
   - `micu_min_weeks` (Integer, default: 0)
   - `micu_max_weeks` (Integer, default: 0)

2. **APP-ICU**
   - `appicu_min_weeks` (Integer, default: 0)
   - `appicu_max_weeks` (Integer, default: 0)

3. **Procedures**
   - `procedures_min_weeks` (Integer, default: 0)
   - `procedures_max_weeks` (Integer, default: 0)

4. **Consults**
   - `consults_min_weeks` (Integer, default: 0)
   - `consults_max_weeks` (Integer, default: 0)

### API Endpoints

All faculty management endpoints (`/api/admin/faculty`) now support these fields:

#### Create Faculty
```bash
POST /api/admin/faculty
{
  "id": "ABC123",
  "name": "Dr. Jane Smith",
  "email": "jane.smith@uva.edu",
  "rank": "associate",
  "clinical_effort_pct": 50,
  "base_points": 100,
  "eligible_moonlighter": true,
  "available_points": 100,
  "bid_priority": 5,
  "micu_min_weeks": 8,
  "micu_max_weeks": 12,
  "appicu_min_weeks": 0,
  "appicu_max_weeks": 4,
  "procedures_min_weeks": 4,
  "procedures_max_weeks": 8,
  "consults_min_weeks": 0,
  "consults_max_weeks": 0
}
```

#### Update Faculty
```bash
PATCH /api/admin/faculty/{faculty_id}
{
  "available_points": 85,
  "bid_priority": 10,
  "micu_max_weeks": 14
}
```

#### Get Faculty Stats
```bash
GET /api/admin/faculty/stats/summary
```

Returns enhanced statistics including:
- Moonlighter count
- Service capacity by domain (total max weeks available)

---

## Feature 2: Heatmap Visualization System

### Concept

The heatmap calculates dynamic point costs for each week based on:
- Number of unavailability requests
- Available faculty pool
- Required coverage

This creates a market-based incentive system where:
- High-demand weeks cost more points
- Low-demand weeks cost fewer points
- Faculty can see real-time scarcity

### Week Generation

The system generates 52 weeks for a schedule year with preset characteristics:

**High-Demand Periods (Preset):**
- **Weeks 1-6** (Summer: July 6 - Aug 16): 40 points, 85% pressure
- **Week 40** (Spring Break: ~April 1): 35 points, 75% pressure
- **Weeks 25-26** (Christmas): 30 points, 70% pressure
- **Week 21** (Thanksgiving): 25 points, 60% pressure
- **All other weeks** (Regular): 5 points base, 20% pressure

### Key Formulas

#### Pressure Score
```python
pressure = requests_count / (total_faculty - required_coverage)
```
- Range: 0.0 (no pressure) to 1.0 (maximum pressure)

#### Dynamic Point Cost
```python
multiplier = 1 + (max_multiplier - 1) * (pressure ** 2)
cost = base_cost * multiplier
```
- Base cost: 5 points
- Max multiplier: 10x
- Uses quadratic scaling to make high-demand weeks significantly more expensive

#### Status Categories
- **Low** (🟢): pressure < 30% → 5-7 points
- **Medium** (🟡): 30% ≤ pressure < 60% → 8-14 points  
- **High** (🟠): 60% ≤ pressure < 90% → 15-25 points
- **Critical** (🔴): pressure ≥ 90% → 30+ points

### API Endpoints

#### Initialize Schedule Year
```bash
POST /api/heatmap/initialize-year
{
  "start_date": "2025-07-06"
}
```

Creates 52 weeks starting from the specified date with preset demand characteristics.

#### Get Full Heatmap
```bash
GET /api/heatmap/full
```

Returns array of all 52 weeks with:
- Week number and label
- Date range
- Current requests count
- Max capacity
- Pressure score
- Point cost
- Status (low/medium/high/critical)
- Spots remaining

#### Get Calendar View
```bash
GET /api/heatmap/calendar
```

Returns heatmap data grouped by month for calendar display, plus summary statistics.

#### Get Week Details
```bash
GET /api/heatmap/week/W01
```

Returns detailed metrics for a specific week including:
- Current pressure and cost
- Alternative low-cost weeks nearby

#### Update Week Metrics
```bash
POST /api/heatmap/week/W01/update
```

Recalculates pressure and cost after requests are added/removed.

#### Update All Weeks
```bash
POST /api/heatmap/update-all
```

Recalculates metrics for all 52 weeks (useful after bulk operations).

#### Upload Historic Data
```bash
POST /api/heatmap/upload-historic
{
  "data": [
    {"week_number": 1, "request_count": 18},
    {"week_number": 2, "request_count": 15},
    {"week_number": 40, "request_count": 16}
  ]
}
```

Adjusts initial point costs based on historic request patterns.

#### Get Pattern Analysis
```bash
GET /api/heatmap/analysis
```

Returns:
- Chronic high-demand weeks
- Moderate demand weeks
- Low-demand weeks
- Total requests
- Average pressure
- Spots available

#### Create Snapshot
```bash
POST /api/heatmap/snapshot
```

Takes a snapshot of current heatmap state for historical tracking and trend analysis.

### Database Models

#### VacationWeek (Enhanced)
```python
id: String              # "W01", "W02", etc.
week_number: Integer    # 1-52
start_date: Date
end_date: Date
week_type: String       # regular, summer, spring_break, thanksgiving, christmas
point_cost_off: Integer # Dynamic cost to take week off
current_requests: Integer   # NEW: Number of current requests
max_capacity: Integer       # NEW: Max people who can be unavailable
pressure_score: Float       # NEW: 0.0-1.0 scarcity indicator
```

#### WeekHeatmapHistory (New)
```python
id: Integer
week_id: String
snapshot_date: Date
requests_count: Integer
capacity: Integer
pressure_score: Float
point_cost: Integer
```

Tracks historical heatmap data for pattern analysis.

---

## Usage Example

### Setting Up a Schedule Year

```python
# 1. Initialize 52 weeks starting July 6, 2025
POST /api/heatmap/initialize-year
{"start_date": "2025-07-06"}

# 2. (Optional) Upload historic data to adjust costs
POST /api/heatmap/upload-historic
{
  "data": [
    {"week_number": 1, "request_count": 18},
    {"week_number": 2, "request_count": 17},
    {"week_number": 40, "request_count": 16},
    {"week_number": 21, "request_count": 14},
    {"week_number": 25, "request_count": 19},
    {"week_number": 26, "request_count": 20}
  ]
}

# 3. Get heatmap for display
GET /api/heatmap/calendar

# 4. As requests come in, update specific weeks
POST /api/heatmap/week/W01/update
```

### Faculty Workflow

1. Faculty logs in and views heatmap
2. Sees Week 1 (summer) costs 45 points (critical demand)
3. Notices Week 3 only costs 8 points (medium demand)
4. Decides to request Week 3 instead to conserve points
5. System updates heatmap automatically

---

## Migration Notes

### Database Migration

The enhanced models add new columns to existing tables. When deploying:

1. Backup your database
2. The `init_db()` function will add new columns with defaults
3. Existing faculty will have:
   - `eligible_moonlighter = False`
   - `available_points = 100`
   - `bid_priority = 0`
   - All service week allocations = 0

4. Admin should update faculty records with appropriate values

### Typical Service Week Allocations

Example for full-time faculty (100% clinical):
```python
micu_min_weeks: 8-10
micu_max_weeks: 12-14
appicu_min_weeks: 4-6
appicu_max_weeks: 6-8
procedures_min_weeks: 4-6
procedures_max_weeks: 6-8
consults_min_weeks: 2-4
consults_max_weeks: 4-6
```

---

## Future Enhancements

Potential additions based on this foundation:

1. **Real-time WebSocket Updates** - Push heatmap changes to connected clients
2. **Historical Trend Visualization** - Charts showing how pressure evolved
3. **Predictive Analytics** - ML-based forecasting of future demand
4. **Alternative Week Suggestions** - Smart recommendations for flexible faculty
5. **Group Coordination** - Tools for faculty to coordinate unavailability
6. **Automated Point Adjustments** - Dynamic point allocation based on rank/effort

---

## Testing

To test the new features:

```bash
# 1. Start the server
cd backend
python -m uvicorn app:app --reload

# 2. Initialize a schedule year
curl -X POST http://localhost:8000/api/heatmap/initialize-year \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2025-07-06"}'

# 3. Create a faculty member with new fields
curl -X POST http://localhost:8000/api/admin/faculty \
  -H "Content-Type: application/json" \
  -d '{
    "id": "TEST123",
    "name": "Dr. Test",
    "email": "test@uva.edu",
    "rank": "associate",
    "clinical_effort_pct": 50,
    "base_points": 100,
    "eligible_moonlighter": true,
    "available_points": 100,
    "bid_priority": 5,
    "micu_min_weeks": 8,
    "micu_max_weeks": 12
  }'

# 4. Get the heatmap
curl http://localhost:8000/api/heatmap/calendar
```

---

## Questions or Issues?

This branch represents a significant enhancement to the scheduling system. Please review thoroughly and test with sample data before merging to production.
