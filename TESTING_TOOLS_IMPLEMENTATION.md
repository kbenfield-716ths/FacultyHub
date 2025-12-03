# Testing Tools Implementation Guide

## Overview
This guide explains how to add the Testing Tools features to admin.html for easy faculty impersonation and data reset during testing cycles.

## Backend APIs (Already Implemented)

The following endpoints are now available:

### Impersonation
- `POST /api/admin/impersonate/{faculty_id}` - Login as any faculty member
- Returns session cookie, no password required
- Admin only

### Reset Utilities
- `POST /api/admin/reset/points` - Reset all faculty bonus points to 0
- `POST /api/admin/reset/requests?year=2026` - Clear unavailability requests
- `POST /api/admin/reset/all?year=2026` - Complete reset (points + requests)

## Frontend Changes Needed

### 1. Add Testing Tools Tab Button

In the `admin-tabs` div, after the "Manage Weeks" button, add:

```html
<button class="tab-btn" onclick="showTab('testing')">🧪 Testing Tools</button>
```

### 2. Add "Login As" Button to Faculty Table

In the `loadFaculty()` function, update the action buttons section:

```javascript
row.innerHTML = `
  <td><strong>${f.id}</strong></td>
  <td>${f.name}</td>
  ... existing columns ...
  <td>
    <div class="action-buttons">
      <button class="btn-success" onclick="impersonateFaculty('${f.id}', '${f.name}')">🔐 Login As</button>
      <button class="btn-secondary" onclick="editFaculty('${f.id}')">Edit</button>
      <button class="btn-${f.is_admin ? 'danger' : 'success'}" onclick="toggleAdmin('${f.id}', ${f.is_admin})">${f.is_admin ? 'Remove Admin' : 'Make Admin'}</button>
      <button class="btn-danger" onclick="deleteFaculty('${f.id}', '${f.name}')">Delete</button>
    </div>
  </td>
`;
```

### 3. Add Testing Tools Tab Content

After the `tab-weeks` div, add:

```html
<div id="tab-testing" class="tab-content">
  <div class="card">
    <div class="card-header">
      <h2 class="card-title">🧪 Testing Utilities</h2>
      <p style="color: #dc2626; font-size: 13px; font-weight: 600;">⚠️ Admin Only - Use for testing workflows</p>
    </div>
    
    <div style="margin-bottom: 40px;">
      <h3 style="margin-bottom: 16px; color: #1f2937;">Faculty Impersonation</h3>
      <p style="color: #6b7280; margin-bottom: 16px; line-height: 1.6;">
        Click "Login As" next to any faculty member in the Manage Providers tab to instantly switch to their account.
        No password required. Perfect for testing the faculty workflow from different perspectives.
      </p>
      <div style="padding: 16px; background: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 8px;">
        <strong style="color: #92400e;">💡 Tip:</strong> 
        <span style="color: #78350f;">After testing, logout and log back in as admin to return to admin view.</span>
      </div>
    </div>
    
    <div style="margin-bottom: 40px;">
      <h3 style="margin-bottom: 16px; color: #1f2937;">Reset Utilities</h3>
      <p style="color: #6b7280; margin-bottom: 24px; line-height: 1.6;">
        Use these tools to reset data between testing cycles. Perfect for testing the point-based allocation system multiple times.
      </p>
      
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px;">
        <div style="padding: 24px; background: white; border: 2px solid #e5e7eb; border-radius: 12px;">
          <h4 style="margin-bottom: 12px; color: #1f2937; font-size: 16px;">Reset Faculty Points</h4>
          <p style="color: #6b7280; font-size: 13px; margin-bottom: 16px; line-height: 1.5;">
            Reset all faculty bonus points to 0. Base points remain intact.
          </p>
          <button class="btn-primary" onclick="resetPoints()" style="width: 100%;">Reset All Points</button>
        </div>
        
        <div style="padding: 24px; background: white; border: 2px solid #e5e7eb; border-radius: 12px;">
          <h4 style="margin-bottom: 12px; color: #1f2937; font-size: 16px;">Clear Requests</h4>
          <p style="color: #6b7280; font-size: 13px; margin-bottom: 16px; line-height: 1.5;">
            Delete all unavailability requests. Faculty and weeks remain.
          </p>
          <div style="margin-bottom: 12px;">
            <label style="display: block; font-size: 12px; color: #6b7280; margin-bottom: 4px;">Year (optional)</label>
            <input type="number" id="resetYear" placeholder="2026" style="width: 100%; padding: 8px; border: 2px solid #e5e7eb; border-radius: 6px;">
          </div>
          <button class="btn-danger" onclick="resetRequests()" style="width: 100%;">Clear Requests</button>
        </div>
        
        <div style="padding: 24px; background: white; border: 2px solid #e5e7eb; border-radius: 12px;">
          <h4 style="margin-bottom: 12px; color: #1f2937; font-size: 16px;">Complete Reset</h4>
          <p style="color: #6b7280; font-size: 13px; margin-bottom: 16px; line-height: 1.5;">
            Reset points AND clear requests. Fresh start for testing.
          </p>
          <div style="margin-bottom: 12px;">
            <label style="display: block; font-size: 12px; color: #6b7280; margin-bottom: 4px;">Year (optional)</label>
            <input type="number" id="resetAllYear" placeholder="2026" style="width: 100%; padding: 8px; border: 2px solid #e5e7eb; border-radius: 6px;">
          </div>
          <button class="btn-danger" onclick="resetAll()" style="width: 100%; background: #dc2626;">Complete Reset</button>
        </div>
      </div>
    </div>
    
    <div id="testingAlert" class="alert"></div>
  </div>
</div>
```

### 4. Add JavaScript Functions

Add these functions to the `<script>` section:

```javascript
// Impersonate a faculty member for testing
async function impersonateFaculty(facultyId, name) {
  if (!confirm(`Switch to ${name}'s account?\n\nYou'll be logged in as this faculty member.`)) return;
  
  try {
    const response = await fetch(`/api/admin/impersonate/${facultyId}`, {
      method: 'POST',
      credentials: 'same-origin'
    });
    
    if (!response.ok) throw new Error('Failed to impersonate faculty');
    
    const data = await response.json();
    alert(`✅ Now logged in as ${data.faculty_name}\n\nRedirecting to home page...`);
    
    // Redirect to home page as the impersonated user
    setTimeout(() => {
      window.location.href = '/index.html';
    }, 1000);
  } catch (error) {
    alert(`Error: ${error.message}`);
  }
}

// Reset all faculty bonus points
async function resetPoints() {
  if (!confirm('Reset all faculty bonus points to 0?\n\nBase points will remain intact.\n\nThis cannot be undone.')) return;
  
  try {
    const response = await fetch('/api/admin/reset/points', {
      method: 'POST',
      credentials: 'same-origin'
    });
    
    if (!response.ok) throw new Error('Failed to reset points');
    
    const data = await response.json();
    showAlert('testingAlert', `✅ ${data.message}`, 'success');
    await loadFaculty();
  } catch (error) {
    showAlert('testingAlert', `Error: ${error.message}`, 'error');
  }
}

// Clear all unavailability requests
async function resetRequests() {
  const year = document.getElementById('resetYear').value;
  const yearText = year ? ` for ${year}` : '';
  
  if (!confirm(`Delete ALL unavailability requests${yearText}?\n\nFaculty and weeks will remain.\n\nThis cannot be undone.`)) return;
  
  try {
    const url = year 
      ? `/api/admin/reset/requests?year=${year}`
      : '/api/admin/reset/requests';
    
    const response = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin'
    });
    
    if (!response.ok) throw new Error('Failed to reset requests');
    
    const data = await response.json();
    showAlert('testingAlert', `✅ ${data.message}`, 'success');
    await loadRequests();
  } catch (error) {
    showAlert('testingAlert', `Error: ${error.message}`, 'error');
  }
}

// Complete reset: points + requests
async function resetAll() {
  const year = document.getElementById('resetAllYear').value;
  const yearText = year ? ` for ${year}` : '';
  
  if (!confirm(`⚠️ COMPLETE RESET${yearText}\n\n• Reset all faculty bonus points\n• Delete all unavailability requests\n\nThis cannot be undone!`)) return;
  
  try {
    const url = year 
      ? `/api/admin/reset/all?year=${year}`
      : '/api/admin/reset/all';
    
    const response = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin'
    });
    
    if (!response.ok) throw new Error('Failed to complete reset');
    
    const data = await response.json();
    showAlert('testingAlert', `✅ ${data.message}`, 'success');
    await loadFaculty();
    await loadRequests();
  } catch (error) {
    showAlert('testingAlert', `Error: ${error.message}`, 'error');
  }
}
```

## Usage Workflow

### Testing a Faculty Workflow
1. Go to "Manage Providers" tab
2. Click "🔐 Login As" next to any faculty member
3. You're instantly logged in as them
4. Test their view, make unavailability requests, etc.
5. Logout and log back in as admin

### Resetting for Another Test Cycle
1. Go to "Testing Tools" tab
2. Click "Complete Reset" to clear all points and requests
3. Optionally specify a year to only reset that year
4. Start fresh with 21 faculty testing again

## Benefits

✅ **No more logging in/out 21 times** - One click to switch accounts
✅ **Test point economics** - Reset and run multiple cycles to see how points work
✅ **Verify fairness** - See the system from each faculty's perspective
✅ **Clean testing** - Easy reset between cycles
✅ **Safe** - Admin only, clearly marked as testing tools

## Security Notes

- All endpoints require admin authentication
- Impersonation creates a new session (doesn't compromise passwords)
- Reset operations have confirmation dialogs
- Can't be accessed by regular faculty users
