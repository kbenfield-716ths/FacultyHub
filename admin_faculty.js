// admin_faculty.js
// Faculty Management for Admin Panel

class FacultyManager {
    constructor(apiBaseUrl) {
        this.apiBaseUrl = apiBaseUrl;
        this.facultyList = [];
    }

    // ==========================================
    // API CALLS
    // ==========================================

    async getAllFaculty(activeOnly = false) {
        const response = await fetch(`${this.apiBaseUrl}/admin/faculty?active_only=${activeOnly}`, {
            headers: {
                'Authorization': `Bearer ${this.getAuthToken()}`
            }
        });
        if (!response.ok) throw new Error('Failed to fetch faculty');
        this.facultyList = await response.json();
        return this.facultyList;
    }

    async getFaculty(facultyId) {
        const response = await fetch(`${this.apiBaseUrl}/admin/faculty/${facultyId}`, {
            headers: {
                'Authorization': `Bearer ${this.getAuthToken()}`
            }
        });
        if (!response.ok) throw new Error('Faculty not found');
        return await response.json();
    }

    async createFaculty(facultyData) {
        const response = await fetch(`${this.apiBaseUrl}/admin/faculty`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.getAuthToken()}`
            },
            body: JSON.stringify(facultyData)
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create faculty');
        }
        return await response.json();
    }

    async updateFaculty(facultyId, updateData) {
        const response = await fetch(`${this.apiBaseUrl}/admin/faculty/${facultyId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.getAuthToken()}`
            },
            body: JSON.stringify(updateData)
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to update faculty');
        }
        return await response.json();
    }

    async deleteFaculty(facultyId) {
        const response = await fetch(`${this.apiBaseUrl}/admin/faculty/${facultyId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${this.getAuthToken()}`
            }
        });
        if (!response.ok) throw new Error('Failed to delete faculty');
        return true;
    }

    async resetPassword(facultyId, newPassword) {
        const response = await fetch(`${this.apiBaseUrl}/admin/faculty/${facultyId}/reset-password`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.getAuthToken()}`
            },
            body: JSON.stringify({ new_password: newPassword })
        });
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to reset password');
        }
        return await response.json();
    }

    async toggleAdmin(facultyId) {
        const response = await fetch(`${this.apiBaseUrl}/admin/faculty/${facultyId}/toggle-admin`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.getAuthToken()}`
            }
        });
        if (!response.ok) throw new Error('Failed to toggle admin status');
        return await response.json();
    }

    async getStats() {
        const response = await fetch(`${this.apiBaseUrl}/admin/faculty/stats/summary`, {
            headers: {
                'Authorization': `Bearer ${this.getAuthToken()}`
            }
        });
        if (!response.ok) throw new Error('Failed to fetch stats');
        return await response.json();
    }

    // ==========================================
    // UI RENDERING
    // ==========================================

    renderFacultyTable(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        let html = `
            <div class="faculty-table-container">
                <div class="table-header">
                    <h3>Faculty Members</h3>
                    <button onclick="facultyManager.showAddModal()" class="btn-primary">
                        ➕ Add Faculty
                    </button>
                </div>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Name</th>
                            <th>Email</th>
                            <th>Rank</th>
                            <th>Effort %</th>
                            <th>Base Points</th>
                            <th>Bonus Points</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        this.facultyList.forEach(faculty => {
            const statusBadge = faculty.active 
                ? '<span class="badge badge-success">Active</span>'
                : '<span class="badge badge-danger">Inactive</span>';
            
            const adminBadge = faculty.is_admin 
                ? '<span class="badge badge-warning">Admin</span>'
                : '';

            html += `
                <tr>
                    <td><strong>${faculty.id}</strong></td>
                    <td>${faculty.name}</td>
                    <td>${faculty.email}</td>
                    <td>${this.formatRank(faculty.rank)}</td>
                    <td>${faculty.clinical_effort_pct}%</td>
                    <td>${faculty.base_points}</td>
                    <td>${faculty.bonus_points}</td>
                    <td>${statusBadge} ${adminBadge}</td>
                    <td class="action-buttons">
                        <button onclick="facultyManager.showEditModal('${faculty.id}')" 
                                class="btn-small btn-primary">Edit</button>
                        <button onclick="facultyManager.showPasswordModal('${faculty.id}')" 
                                class="btn-small btn-secondary">Reset PW</button>
                        <button onclick="facultyManager.confirmDelete('${faculty.id}')" 
                                class="btn-small btn-danger">Delete</button>
                    </td>
                </tr>
            `;
        });

        html += `
                    </tbody>
                </table>
            </div>
        `;

        container.innerHTML = html;
    }

    // ==========================================
    // MODAL DIALOGS
    // ==========================================

    showAddModal() {
        const modal = document.getElementById('facultyModal');
        if (!modal) this.createModalHTML();

        document.getElementById('modalTitle').textContent = 'Add Faculty Member';
        document.getElementById('facultyForm').reset();
        document.getElementById('facultyId').value = '';
        document.getElementById('facultyIdField').style.display = 'block';
        document.getElementById('facultyModal').style.display = 'flex';
    }

    async showEditModal(facultyId) {
        const faculty = await this.getFaculty(facultyId);
        
        document.getElementById('modalTitle').textContent = 'Edit Faculty Member';
        document.getElementById('facultyId').value = faculty.id;
        document.getElementById('facultyIdField').style.display = 'none';
        document.getElementById('name').value = faculty.name;
        document.getElementById('email').value = faculty.email;
        document.getElementById('rank').value = faculty.rank;
        document.getElementById('clinical_effort_pct').value = faculty.clinical_effort_pct;
        document.getElementById('base_points').value = faculty.base_points;
        document.getElementById('bonus_points').value = faculty.bonus_points;
        document.getElementById('is_admin').checked = faculty.is_admin;
        document.getElementById('active').checked = faculty.active;
        
        document.getElementById('facultyModal').style.display = 'flex';
    }

    showPasswordModal(facultyId) {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <h3>Reset Password</h3>
                <p>Enter new password for this faculty member:</p>
                <input type="password" id="newPassword" placeholder="New password (min 8 characters)" />
                <div class="modal-actions">
                    <button onclick="this.closest('.modal').remove()" class="btn-secondary">Cancel</button>
                    <button onclick="facultyManager.resetPasswordConfirm('${facultyId}')" class="btn-primary">Reset</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        modal.style.display = 'flex';
    }

    async resetPasswordConfirm(facultyId) {
        const newPassword = document.getElementById('newPassword').value;
        if (!newPassword || newPassword.length < 8) {
            alert('Password must be at least 8 characters');
            return;
        }

        try {
            await this.resetPassword(facultyId, newPassword);
            alert('Password reset successfully');
            document.querySelector('.modal').remove();
        } catch (error) {
            alert(`Error: ${error.message}`);
        }
    }

    async confirmDelete(facultyId) {
        if (!confirm('Are you sure you want to deactivate this faculty member?')) return;

        try {
            await this.deleteFaculty(facultyId);
            await this.refreshTable();
            alert('Faculty member deactivated');
        } catch (error) {
            alert(`Error: ${error.message}`);
        }
    }

    closeModal() {
        document.getElementById('facultyModal').style.display = 'none';
    }

    // ==========================================
    // FORM SUBMISSION
    // ==========================================

    async saveFaculty(event) {
        event.preventDefault();

        const formData = {
            id: document.getElementById('newFacultyId').value,
            name: document.getElementById('name').value,
            email: document.getElementById('email').value,
            rank: document.getElementById('rank').value,
            clinical_effort_pct: parseInt(document.getElementById('clinical_effort_pct').value),
            base_points: parseInt(document.getElementById('base_points').value),
            bonus_points: parseInt(document.getElementById('bonus_points').value),
            is_admin: document.getElementById('is_admin').checked,
            active: document.getElementById('active').checked
        };

        try {
            const existingId = document.getElementById('facultyId').value;
            
            if (existingId) {
                // Update existing
                delete formData.id; // Can't change ID
                await this.updateFaculty(existingId, formData);
                alert('Faculty updated successfully');
            } else {
                // Create new
                await this.createFaculty(formData);
                alert('Faculty created successfully');
            }

            this.closeModal();
            await this.refreshTable();
        } catch (error) {
            alert(`Error: ${error.message}`);
        }
    }

    // ==========================================
    // UTILITIES
    // ==========================================

    async refreshTable() {
        await this.getAllFaculty();
        this.renderFacultyTable('facultyTableContainer');
    }

    formatRank(rank) {
        const ranks = {
            'assistant': 'Assistant',
            'associate': 'Associate',
            'full': 'Full Professor'
        };
        return ranks[rank] || rank;
    }

    getAuthToken() {
        // Retrieve from localStorage or session
        return localStorage.getItem('authToken') || '';
    }

    createModalHTML() {
        const modalHTML = `
            <div id="facultyModal" class="modal" style="display: none;">
                <div class="modal-content">
                    <h2 id="modalTitle">Add Faculty</h2>
                    <form id="facultyForm" onsubmit="facultyManager.saveFaculty(event)">
                        <input type="hidden" id="facultyId" />
                        
                        <div id="facultyIdField" class="form-group">
                            <label>Computing ID</label>
                            <input type="text" id="newFacultyId" required placeholder="KE4Z" />
                        </div>

                        <div class="form-group">
                            <label>Name</label>
                            <input type="text" id="name" required />
                        </div>

                        <div class="form-group">
                            <label>Email</label>
                            <input type="email" id="email" required />
                        </div>

                        <div class="form-group">
                            <label>Rank</label>
                            <select id="rank" required>
                                <option value="assistant">Assistant Professor</option>
                                <option value="associate">Associate Professor</option>
                                <option value="full">Full Professor</option>
                            </select>
                        </div>

                        <div class="form-group">
                            <label>Clinical Effort %</label>
                            <input type="number" id="clinical_effort_pct" min="0" max="100" required />
                        </div>

                        <div class="form-group">
                            <label>Base Points</label>
                            <input type="number" id="base_points" min="0" required />
                        </div>

                        <div class="form-group">
                            <label>Bonus Points</label>
                            <input type="number" id="bonus_points" min="0" value="0" />
                        </div>

                        <div class="form-group">
                            <label>
                                <input type="checkbox" id="is_admin" />
                                Administrator
                            </label>
                        </div>

                        <div class="form-group">
                            <label>
                                <input type="checkbox" id="active" checked />
                                Active
                            </label>
                        </div>

                        <div class="modal-actions">
                            <button type="button" onclick="facultyManager.closeModal()" class="btn-secondary">Cancel</button>
                            <button type="submit" class="btn-primary">Save</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }
}

// Initialize
const facultyManager = new FacultyManager('/api');

// Load on page ready
document.addEventListener('DOMContentLoaded', async () => {
    await facultyManager.getAllFaculty();
    facultyManager.renderFacultyTable('facultyTableContainer');
});
