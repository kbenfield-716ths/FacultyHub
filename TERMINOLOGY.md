# Terminology Reference - PCCM Faculty Hub

## ✅ Correct Terms to Use

### The System
- **PCCM Faculty Hub** - The overall application name
- **Faculty Hub** - Short form
- **Inpatient Service Scheduling** - The weeks/availability system
- **Service Availability** - When faculty indicate availability for inpatient service

### The Two Systems

#### 1. Moonlighting System
- **Moonlighting** - Extra night shifts faculty can request
- **Moonlighting Shifts** - The individual night shifts available
- **Shift Requests** - When faculty request moonlighting nights
- **Shift Assignments** - Final schedule of who works which nights

#### 2. Service Availability System
- **Service Weeks** - The 52 weeks of the academic year
- **Availability Requests** - Faculty indicating when they can/cannot work
- **Unavailable** - Faculty CANNOT work inpatient service (costs points)
- **Available** - Faculty CAN work if needed (neutral, no points)
- **Volunteering** - Faculty requests to work holiday weeks (earns bonus points)
- **Points System** - Budget system for managing time off
- **Service Coverage** - Ensuring minimum staff for inpatient duties

### Database Tables (Current vs Should Be)

| Current Name | Should Be | Description |
|-------------|-----------|-------------|
| `Faculty` | ✅ Correct | Faculty members with profiles |
| `VacationWeek` | `ServiceWeek` | The 52 weeks for scheduling |
| `VacationRequest` | `ServiceRequest` | Faculty availability for each week |
| `Provider` | ✅ Correct | Moonlighting system (legacy) |
| `Shift` | ✅ Correct | Moonlighting shifts |
| `Signup` | ✅ Correct | Moonlighting requests |
| `Assignment` | ✅ Correct | Final moonlighting schedule |

## ❌ Terms to AVOID

### Never Use These:
- ~~**Vacation**~~ - This is NOT a vacation system!
- ~~**Vacation requests**~~ - Say "availability requests"
- ~~**Vacation weeks**~~ - Say "service weeks" 
- ~~**Time off**~~ - Say "unavailable for service"
- ~~**PTO**~~ - Not applicable here
- ~~**Leave**~~ - Not applicable here

## 📝 Example Usage

### ✅ Good Examples:

"Faculty can indicate when they're **unavailable for inpatient service**"

"The **service availability system** manages the 52-week schedule"

"Faculty earn **base points** based on their **clinical effort** and **rank**"

"Being **unavailable** during a week **costs points** from your budget"

"**Volunteering** for holiday coverage **earns bonus points**"

"The **points system** ensures fair distribution of service responsibilities"

### ❌ Bad Examples:

~~"Faculty can request vacation weeks"~~ → "Faculty can indicate unavailable weeks"

~~"Vacation scheduling system"~~ → "Service availability system"

~~"Taking time off costs points"~~ → "Being unavailable costs points"

~~"Request vacation during holidays"~~ → "Indicate availability for holiday weeks"

## 🎯 The Core Concept

This is **NOT** about vacations. It's about:

1. **Inpatient Service Duty** - Faculty rotate through covering the inpatient service
2. **Availability Management** - Faculty have other commitments (research, clinics, conferences, yes sometimes personal time)
3. **Fair Scheduling** - Points system ensures equitable distribution of service weeks
4. **Coverage Assurance** - Minimum staff maintained (typically 5 faculty per week)
5. **Holiday Incentives** - Bonus points for covering high-demand periods

## 🏥 Real-World Context

Think of it like this:

- **Moonlighting** = Extra shifts faculty WANT (earn extra money)
- **Service Availability** = Regular service weeks faculty MUST cover (part of job)
  - Faculty get a budget of points to spend on being unavailable
  - Similar to how NFL teams have salary caps
  - Holidays cost more points (high demand)
  - Summer costs fewer points (lower demand)
  - Volunteering for holidays earns bonus points for next year

## 📋 UI Text Examples

### Login Page:
✅ "PCCM Faculty Hub - Manage your moonlighting and service availability"
❌ ~~"PCCM Scheduler - Vacation and moonlighting"~~

### Navigation:
✅ "Service Availability" or "Inpatient Scheduling"
❌ ~~"Vacation Weeks"~~

### Status Labels:
✅ "Unavailable" / "Available" / "Volunteering"
❌ ~~"Off" / "On Duty" / "Requested PTO"~~

### Points Display:
✅ "Available Points for Service Flexibility"
❌ ~~"Vacation Points Balance"~~

### Week Details:
✅ "Cost: -5 pts (if unavailable)" and "Reward: +5 pts (if volunteer)"
❌ ~~"Vacation cost: -5 pts"~~

## 🔄 Refactoring Checklist

When you see these in code, update them:

- [ ] `VacationWeek` → `ServiceWeek`
- [ ] `VacationRequest` → `ServiceRequest`
- [ ] `vacation_weeks` table → `service_weeks`
- [ ] `vacation_requests` table → `service_requests`
- [ ] Any variable/comment with "vacation" → appropriate service term
- [ ] UI text with "vacation" → "service availability"

## 💡 Remember

**This system helps faculty balance:**
- Clinical service obligations
- Research commitments  
- Educational responsibilities
- Personal time
- Conference attendance
- Administrative duties

It's a **workforce management tool** for academic medicine, not a vacation planner!
