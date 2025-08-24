// Enhanced Admin Dashboard JavaScript
class EnhancedAdminDashboard {
    constructor() {
        this.apiBaseUrl = '/api/';
        this.token = localStorage.getItem('admin_token') || localStorage.getItem('access_token');
        this.adminInfo = JSON.parse(localStorage.getItem('admin_info') || localStorage.getItem('user_info') || '{}');
        this.init();
    }

    init() {
        this.checkAuthentication();
        this.loadDashboardData();
        this.setupEventListeners();
    }

    checkAuthentication() {
        if (!this.token) {
            this.redirectToLogin();
            return;
        }

        // Update admin name in navigation
        if (this.adminInfo.first_name) {
            document.getElementById('adminName').textContent = `${this.adminInfo.first_name} ${this.adminInfo.last_name}`;
        }
    }

    setupEventListeners() {
        // Logout functionality
        window.logout = () => this.logout();
    }

    async loadDashboardData() {
        await Promise.all([
            this.loadEnhancedDashboard(),
            this.loadSystemStatus()
        ]);
    }

    async loadEnhancedDashboard() {
        try {
            const response = await this.makeAuthenticatedRequest('admin/enhanced-dashboard/');
            if (response.ok) {
                const data = await response.json();
                this.updateStatistics(data.stats);
                this.updateRecentFeedbacks(data.recent_feedbacks);
                this.updateRecentPredictions(data.recent_predictions);
                this.updateRecentUploads(data.recent_uploads);
            } else {
                throw new Error('Failed to load dashboard data');
            }
        } catch (error) {
            console.error('Error loading enhanced dashboard:', error);
            this.showAlert('Error loading dashboard data', 'danger');
        }
    }

    async loadSystemStatus() {
        try {
            const response = await this.makeAuthenticatedRequest('models/status/');
            if (response.ok) {
                const data = await response.json();
                this.updateSystemStatus(data);
            }
        } catch (error) {
            console.error('Error loading system status:', error);
        }
    }

    updateStatistics(stats) {
        document.getElementById('totalStudents').textContent = stats.total_students || 0;
        document.getElementById('totalAdmins').textContent = stats.total_admins || 0;
        document.getElementById('totalPredictions').textContent = stats.total_predictions || 0;
        document.getElementById('totalChats').textContent = stats.total_chats || 0;
        document.getElementById('totalFeedbacks').textContent = stats.total_feedbacks || 0;
        document.getElementById('pendingUploads').textContent = stats.pending_uploads || 0;
    }

    updateRecentFeedbacks(feedbacks) {
        const container = document.getElementById('recentFeedbacks');
        
        if (!feedbacks || feedbacks.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-comment-dots"></i>
                    <p>No feedbacks yet</p>
                </div>
            `;
            return;
        }

        const feedbacksHtml = feedbacks.map(feedback => `
            <div class="activity-item d-flex align-items-center">
                <div class="activity-icon bg-primary">
                    <i class="fas fa-user"></i>
                </div>
                <div class="activity-content">
                    <div class="activity-title">${feedback.student_name}</div>
                    <div class="activity-meta">
                        ${feedback.feedback.length > 50 ? feedback.feedback.substring(0, 50) + '...' : feedback.feedback}
                    </div>
                    <small class="text-muted">${new Date(feedback.submitted_at).toLocaleDateString()}</small>
                </div>
                <div class="ms-auto">
                    ${this.getRatingStars(feedback.rating)}
                </div>
            </div>
        `).join('');

        container.innerHTML = feedbacksHtml;
    }

    updateRecentPredictions(predictions) {
        const container = document.getElementById('recentPredictions');
        
        if (!predictions || predictions.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-chart-line"></i>
                    <p>No predictions yet</p>
                </div>
            `;
            return;
        }

        const predictionsHtml = predictions.map(prediction => `
            <div class="activity-item d-flex align-items-center">
                <div class="activity-icon bg-success">
                    <i class="fas fa-chart-line"></i>
                </div>
                <div class="activity-content">
                    <div class="activity-title">${prediction.student}</div>
                    <div class="activity-meta">
                        ${prediction.stream} | Z-Score: ${prediction.z_score}
                    </div>
                    <small class="text-muted">${new Date(prediction.predicted_at).toLocaleDateString()}</small>
                </div>
                <div class="ms-auto">
                    <span class="badge bg-info">${prediction.total_predictions_generated} results</span>
                </div>
            </div>
        `).join('');

        container.innerHTML = predictionsHtml;
    }

    updateRecentUploads(uploads) {
        const container = document.getElementById('recentUploads');
        
        if (!uploads || uploads.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-upload"></i>
                    <p>No uploads yet</p>
                </div>
            `;
            return;
        }

        const uploadsHtml = uploads.map(upload => `
            <div class="activity-item d-flex align-items-center">
                <div class="activity-icon bg-${this.getStatusColor(upload.processing_status)}">
                    <i class="fas fa-file-pdf"></i>
                </div>
                <div class="activity-content">
                    <div class="activity-title">${upload.filename}</div>
                    <div class="activity-meta">
                        ${upload.file_size} | ${upload.processing_status}
                    </div>
                    <small class="text-muted">${new Date(upload.uploaded_at).toLocaleDateString()}</small>
                </div>
                <div class="ms-auto">
                    <span class="badge bg-${this.getStatusColor(upload.processing_status)}">
                        ${upload.processing_status}
                    </span>
                </div>
            </div>
        `).join('');

        container.innerHTML = uploadsHtml;
    }

    updateSystemStatus(status) {
        const container = document.getElementById('systemStatus');
        
        const statusHtml = `
            <div class="row">
                <div class="col-6 mb-3">
                    <div class="d-flex align-items-center">
                        <i class="fas fa-brain text-${status.models.embeddings_loaded ? 'success' : 'danger'} me-2"></i>
                        <div>
                            <div class="fw-bold">Embeddings Model</div>
                            <small class="text-muted">${status.models.embeddings_loaded ? 'Loaded' : 'Not Loaded'}</small>
                        </div>
                    </div>
                </div>
                <div class="col-6 mb-3">
                    <div class="d-flex align-items-center">
                        <i class="fas fa-robot text-${status.models.llm_loaded ? 'success' : 'danger'} me-2"></i>
                        <div>
                            <div class="fw-bold">LLM Model</div>
                            <small class="text-muted">${status.models.llm_loaded ? 'Loaded' : 'Not Loaded'}</small>
                        </div>
                    </div>
                </div>
                <div class="col-6 mb-3">
                    <div class="d-flex align-items-center">
                        <i class="fas fa-database text-${status.uploads.celery_worker_healthy ? 'success' : 'danger'} me-2"></i>
                        <div>
                            <div class="fw-bold">Celery Worker</div>
                            <small class="text-muted">${status.uploads.celery_worker_healthy ? 'Healthy' : 'Unhealthy'}</small>
                        </div>
                    </div>
                </div>
                <div class="col-6 mb-3">
                    <div class="d-flex align-items-center">
                        <i class="fas fa-clock text-${status.uploads.pending_uploads > 0 ? 'warning' : 'success'} me-2"></i>
                        <div>
                            <div class="fw-bold">Pending Uploads</div>
                            <small class="text-muted">${status.uploads.pending_uploads}</small>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        container.innerHTML = statusHtml;
    }

    getRatingStars(rating) {
        if (!rating) return '<span class="text-muted">No rating</span>';
        
        const stars = '⭐'.repeat(rating);
        const emptyStars = '☆'.repeat(5 - rating);
        return `<span class="rating-stars">${stars}${emptyStars}</span>`;
    }

    getStatusColor(status) {
        switch (status) {
            case 'completed': return 'success';
            case 'processing': return 'warning';
            case 'pending': return 'info';
            case 'failed': return 'danger';
            default: return 'secondary';
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
        localStorage.removeItem('admin_token');
        localStorage.removeItem('access_token');
        localStorage.removeItem('admin_info');
        localStorage.removeItem('user_info');
        window.location.href = '/admin-dashboard/';
    }

    redirectToLogin() {
        window.location.href = '/admin-dashboard/';
    }
}

// Initialize enhanced admin dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new EnhancedAdminDashboard();
});
