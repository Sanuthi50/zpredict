// Profile Management JavaScript
class ProfileManager {
    constructor() {
        this.apiBaseUrl = '/api/';
        this.token = localStorage.getItem('access_token');
        this.userInfo = JSON.parse(localStorage.getItem('user_info') || '{}');
        this.init();
    }

    init() {
        this.checkAuthentication();
        this.loadProfileData();
        this.setupEventListeners();
    }

    checkAuthentication() {
        if (!this.token) {
            this.redirectToLogin();
            return;
        }

        // Update user name in navigation
        if (this.userInfo.first_name) {
            document.getElementById('userName').textContent = `${this.userInfo.first_name} ${this.userInfo.last_name}`;
        }
    }

    setupEventListeners() {
        // Profile form submission
        document.getElementById('profileForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.updateProfile();
        });

        // Logout functionality
        window.logout = () => this.logout();
        
        // Delete account functionality
        window.showDeleteAccountModal = () => this.showDeleteAccountModal();
        window.deleteAccount = () => this.deleteAccount();
    }

    async loadProfileData() {
        try {
            const response = await this.makeAuthenticatedRequest('student/profile/');
            if (response.ok) {
                const data = await response.json();
                this.populateProfileForm(data.profile);
            } else {
                throw new Error('Failed to load profile data');
            }
        } catch (error) {
            console.error('Error loading profile:', error);
            this.showAlert('Error loading profile data', 'danger');
        }

        // Load dashboard statistics for the sidebar
        this.loadDashboardStats();
    }

    populateProfileForm(profile) {
        document.getElementById('firstName').value = profile.first_name || '';
        document.getElementById('lastName').value = profile.last_name || '';
        document.getElementById('email').value = profile.email || '';
        
        // Format and display date joined
        const dateJoined = new Date(profile.date_joined);
        document.getElementById('dateJoined').value = dateJoined.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
        
        // Display account status
        const status = profile.is_active ? 'Active' : 'Inactive';
        const statusClass = profile.is_active ? 'text-success' : 'text-danger';
        document.getElementById('accountStatus').value = status;
        document.getElementById('accountStatus').className = `form-control ${statusClass}`;
    }

    async loadDashboardStats() {
        try {
            const response = await this.makeAuthenticatedRequest('student/dashboard/');
            if (response.ok) {
                const data = await response.json();
                this.updateStatistics(data.statistics);
            }
        } catch (error) {
            console.error('Error loading dashboard stats:', error);
        }
    }

    updateStatistics(stats) {
        document.getElementById('totalPredictions').textContent = stats.total_sessions || 0;
        document.getElementById('totalFeedbacks').textContent = stats.total_feedbacks || 0;
        document.getElementById('totalChats').textContent = stats.total_chats || 0;
        
        // Calculate days active
        const userInfo = JSON.parse(localStorage.getItem('user_info') || '{}');
        if (userInfo.date_joined) {
            const joinedDate = new Date(userInfo.date_joined);
            const today = new Date();
            const daysActive = Math.floor((today - joinedDate) / (1000 * 60 * 60 * 24));
            document.getElementById('daysActive').textContent = daysActive;
        }
    }

    async updateProfile() {
        const firstName = document.getElementById('firstName').value.trim();
        const lastName = document.getElementById('lastName').value.trim();
        const email = document.getElementById('email').value.trim();

        if (!firstName || !lastName || !email) {
            this.showAlert('Please fill in all required fields', 'warning');
            return;
        }

        try {
            const response = await this.makeAuthenticatedRequest('student/profile/', {
                method: 'PUT',
                body: JSON.stringify({
                    first_name: firstName,
                    last_name: lastName,
                    email: email
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.showAlert('Profile updated successfully!', 'success');
                
                // Update local storage with new user info
                const updatedUserInfo = {
                    ...this.userInfo,
                    first_name: data.profile.first_name,
                    last_name: data.profile.last_name,
                    email: data.profile.email
                };
                localStorage.setItem('user_info', JSON.stringify(updatedUserInfo));
                
                // Update navigation
                document.getElementById('userName').textContent = `${data.profile.first_name} ${data.profile.last_name}`;
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Failed to update profile');
            }
        } catch (error) {
            console.error('Error updating profile:', error);
            this.showAlert(error.message, 'danger');
        }
    }

    showDeleteAccountModal() {
        const modal = new bootstrap.Modal(document.getElementById('deleteAccountModal'));
        modal.show();
    }

    async deleteAccount() {
        try {
            const response = await this.makeAuthenticatedRequest('student/delete-account/', {
                method: 'DELETE'
            });

            if (response.ok) {
                this.showAlert('Account deleted successfully!', 'success');
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('deleteAccountModal'));
                modal.hide();
                
                // Redirect to login after a short delay
                setTimeout(() => {
                    this.logout();
                }, 2000);
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Failed to delete account');
            }
        } catch (error) {
            console.error('Delete account error:', error);
            this.showAlert(error.message, 'danger');
        }
    }

    async makeAuthenticatedRequest(endpoint, options = {}) {
        const url = this.apiBaseUrl + endpoint;
        const defaultOptions = {
            headers: {
                'Authorization': `Bearer ${this.token}`,
                'Content-Type': 'application/json',
            },
        };

        return fetch(url, { ...defaultOptions, ...options });
    }

    showAlert(message, type = 'info') {
        // Create alert element
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        // Add to page
        document.body.appendChild(alertDiv);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }

    logout() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user_info');
        window.location.href = '/login/';
    }

    redirectToLogin() {
        window.location.href = '/login/';
    }

    // Utility function to format dates
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }

    // Utility function to calculate days between dates
    calculateDaysActive(dateJoined) {
        const joined = new Date(dateJoined);
        const today = new Date();
        return Math.floor((today - joined) / (1000 * 60 * 60 * 24));
    }
}

// Initialize profile manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ProfileManager();
});
