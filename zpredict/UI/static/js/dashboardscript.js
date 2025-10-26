// Dashboard JavaScript
class DashboardManager {
    constructor() {
        this.apiBaseUrl = '/api/';
        this.token = localStorage.getItem('access_token');
        this.userInfo = JSON.parse(localStorage.getItem('user_info') || '{}');
        this.init();
    }

    init() {
        const isAuthed = this.checkAuthentication();
        if (isAuthed) {
            this.loadDashboardData();
        } else {
            this.showAlert('Please login to view your dashboard.', 'info');
        }
        this.setupEventListeners();
    }

    checkAuthentication() {
        if (!this.token) {
            // Do not hard-redirect; allow page to render with prompt
            return false;
        }

        // Update user name in navigation
        const userNameEl = document.getElementById('userName');
        if (this.userInfo.first_name && userNameEl) {
            userNameEl.textContent = `${this.userInfo.first_name} ${this.userInfo.last_name}`;
        }
        return true;
    }

    async loadDashboardData() {
        if (!this.token) return;
        try {
            const response = await this.makeAuthenticatedRequest('student/dashboard/');
            if (response.ok) {
                const data = await response.json();
                this.updateDashboard(data);
            } else {
                if (response.status === 401) {
                    this.showAlert('Session expired. Please login again.', 'warning');
                    return;
                }
                throw new Error('Failed to load dashboard data');
            }
        } catch (error) {
            console.error('Error loading dashboard:', error);
            this.showAlert('Error loading dashboard data', 'danger');
        }
    }

    updateDashboard(data) {
        // Safely update statistics with null checks
        const stats = data.statistics || {};
        
        const totalSessionsEl = document.getElementById('totalSessions');
        const totalSavedEl = document.getElementById('totalSaved');
        const totalChatsEl = document.getElementById('totalChats');
        const totalFeedbacksEl = document.getElementById('totalFeedbacks');
        
        if (totalSessionsEl) totalSessionsEl.textContent = stats.total_sessions || 0;
        if (totalSavedEl) totalSavedEl.textContent = stats.total_saved_predictions || 0;
        if (totalChatsEl) totalChatsEl.textContent = stats.total_chats || 0;
        if (totalFeedbacksEl) totalFeedbacksEl.textContent = stats.total_feedbacks || 0;

        // Update recent sessions
        this.updateRecentSessions(data.recent_sessions || []);
        
        // Update recent saved predictions
        this.updateRecentSaved(data.recent_saved_predictions || []);
    }

    updateRecentSessions(sessions) {
        const container = document.getElementById('recentSessions');
        
        if (!container) {
            console.warn('recentSessions element not found');
            return;
        }
        
        if (!sessions || sessions.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-chart-line"></i>
                    <p>No prediction sessions yet</p>
                    <a href="/prediction/" class="btn btn-primary btn-sm">Start Your First Prediction</a>
                </div>
            `;
            return;
        }

        const sessionsHtml = sessions.map(session => `
            <div class="activity-item d-flex align-items-center">
                <div class="activity-icon bg-primary">
                    <i class="fas fa-chart-line"></i>
                </div>
                <div class="activity-content">
                    <div class="activity-title">${session.stream} - ${session.year}</div>
                    <div class="activity-meta">
                        Z-Score: ${session.z_score} | District: ${session.district} | 
                        ${new Date(session.predicted_at).toLocaleDateString()}
                    </div>
                </div>
                <div class="ms-auto">
                    <span class="badge bg-${this.getConfidenceColor(session.confidence_level)}">
                        ${session.confidence_level}
                    </span>
                </div>
            </div>
        `).join('');

        container.innerHTML = sessionsHtml;
    }

    updateRecentSaved(savedPredictions) {
        const container = document.getElementById('recentSaved');
        
        if (!container) {
            console.warn('recentSaved element not found');
            return;
        }
        
        if (!savedPredictions || savedPredictions.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-bookmark"></i>
                    <p>No saved predictions yet</p>
                    <a href="/prediction/" class="btn btn-success btn-sm">Make Your First Prediction</a>
                </div>
            `;
            return;
        }

        const predictionsHtml = savedPredictions.map(prediction => `
            <div class="activity-item d-flex align-items-center">
                <div class="activity-icon bg-success">
                    <i class="fas fa-university"></i>
                </div>
                <div class="activity-content">
                    <div class="activity-title">${prediction.course_name}</div>
                    <div class="activity-meta">
                        ${prediction.university_name} | 
                        ${new Date(prediction.saved_at).toLocaleDateString()}
                    </div>
                </div>
                <div class="ms-auto text-end">
                    <div class="fw-bold text-success">${prediction.probability_percentage.toFixed(1)}%</div>
                    <small class="text-muted">Probability</small>
                </div>
            </div>
        `).join('');

        container.innerHTML = predictionsHtml;
    }

    getConfidenceColor(confidence) {
        switch (confidence) {
            case 'high': return 'success';
            case 'medium': return 'warning';
            case 'low': return 'danger';
            default: return 'secondary';
        }
    }

    setupEventListeners() {
        // Logout functionality
        window.logout = () => this.logout();
        
        // Delete account functionality
        window.deleteAccount = () => this.deleteAccount();
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

    async logout() {
        try {
            // Clear local storage
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('user_info');
            
            // Redirect to login
            window.location.href = '/login/';
        } catch (error) {
            console.error('Logout error:', error);
            // Force redirect anyway
            window.location.href = '/login/';
        }
    }

    async deleteAccount() {
        if (!confirm('Are you sure you want to delete your account? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await this.makeAuthenticatedRequest('student/delete-account/', {
                method: 'DELETE'
            });

            if (response.ok) {
                this.showAlert('Account deleted successfully', 'success');
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

    redirectToLogin() {
        window.location.href = '/login/';
    }

    // Utility function to format dates
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    // Utility function to animate numbers
    animateNumber(element, target, duration = 1000) {
        const start = 0;
        const increment = target / (duration / 16);
        let current = start;

        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            element.textContent = Math.floor(current);
        }, 16);
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new DashboardManager();
});

// Add some utility functions for other pages
window.DashboardUtils = {
    // Check if user is authenticated
    isAuthenticated() {
        return !!localStorage.getItem('access_token');
    },

    // Get user info
    getUserInfo() {
        return JSON.parse(localStorage.getItem('user_info') || '{}');
    },

    // Get auth token
    getToken() {
        return localStorage.getItem('access_token');
    },

    // Make authenticated API request
    async apiRequest(endpoint, options = {}) {
        const token = this.getToken();
        if (!token) {
            throw new Error('No authentication token');
        }

        const url = '/api/' + endpoint;
        const defaultOptions = {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
        };

        const response = await fetch(url, { ...defaultOptions, ...options });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.error || `HTTP ${response.status}`);
        }

        return response.json();
    },

    // Show notification
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(notification);

        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    },

    // Format date
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    // Logout function
    logout() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user_info');
        window.location.href = '/login/';
    }
};