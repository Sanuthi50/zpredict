// Feedback Management JavaScript for Admins
class FeedbackManagement {
    constructor() {
        this.apiBaseUrl = '/api/';
        this.token = localStorage.getItem('admin_token') || localStorage.getItem('access_token');
        this.adminInfo = JSON.parse(localStorage.getItem('admin_info') || localStorage.getItem('user_info') || '{}');
        this.allFeedbacks = [];
        this.filteredFeedbacks = [];
        this.init();
    }

    init() {
        this.checkAuthentication();
        this.loadFeedbacks();
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
        // Filter and search functionality
        document.getElementById('ratingFilter').addEventListener('change', () => this.filterFeedbacks());
        document.getElementById('searchInput').addEventListener('input', () => this.filterFeedbacks());
        document.getElementById('sortBy').addEventListener('change', () => this.filterFeedbacks());

        // Logout functionality
        window.logout = () => this.logout();
        
        // Delete feedback functionality
        window.deleteFeedback = (id) => this.showDeleteModal(id);
        window.confirmDeleteFeedback = () => this.confirmDeleteFeedback();
    }

    async loadFeedbacks() {
        try {
            const response = await this.makeAuthenticatedRequest('admin/feedback/');
            if (response.ok) {
                const data = await response.json();
                this.allFeedbacks = data.feedbacks;
                this.filteredFeedbacks = [...this.allFeedbacks];
                this.updateStatistics();
                this.displayFeedbacks();
            } else {
                throw new Error('Failed to load feedbacks');
            }
        } catch (error) {
            console.error('Error loading feedbacks:', error);
            this.showAlert('Error loading feedbacks', 'danger');
        }
    }

    updateStatistics() {
        const totalFeedbacks = this.allFeedbacks.length;
        const uniqueUsers = new Set(this.allFeedbacks.map(f => f.student_email)).size;
        
        // Calculate average rating
        const ratings = this.allFeedbacks.filter(f => f.rating).map(f => f.rating);
        const avgRating = ratings.length > 0 ? (ratings.reduce((a, b) => a + b, 0) / ratings.length).toFixed(1) : '0.0';
        
        // Calculate this month's feedbacks
        const thisMonth = new Date().getMonth();
        const thisYear = new Date().getFullYear();
        const thisMonthFeedbacks = this.allFeedbacks.filter(f => {
            const feedbackDate = new Date(f.submitted_at);
            return feedbackDate.getMonth() === thisMonth && feedbackDate.getFullYear() === thisYear;
        }).length;

        document.getElementById('totalFeedbacks').textContent = totalFeedbacks;
        document.getElementById('avgRating').textContent = avgRating;
        document.getElementById('uniqueUsers').textContent = uniqueUsers;
        document.getElementById('thisMonth').textContent = thisMonthFeedbacks;
    }

    filterFeedbacks() {
        const ratingFilter = document.getElementById('ratingFilter').value;
        const searchTerm = document.getElementById('searchInput').value.toLowerCase();
        const sortBy = document.getElementById('sortBy').value;

        this.filteredFeedbacks = this.allFeedbacks.filter(feedback => {
            // Rating filter
            if (ratingFilter && feedback.rating != ratingFilter) {
                return false;
            }

            // Search filter
            if (searchTerm) {
                const searchText = `${feedback.student_name} ${feedback.student_email} ${feedback.feedback}`.toLowerCase();
                if (!searchText.includes(searchTerm)) {
                    return false;
                }
            }

            return true;
        });

        // Sort feedbacks
        this.sortFeedbacks(sortBy);
        this.displayFeedbacks();
    }

    sortFeedbacks(sortBy) {
        switch (sortBy) {
            case 'newest':
                this.filteredFeedbacks.sort((a, b) => new Date(b.submitted_at) - new Date(a.submitted_at));
                break;
            case 'oldest':
                this.filteredFeedbacks.sort((a, b) => new Date(a.submitted_at) - new Date(b.submitted_at));
                break;
            case 'rating-high':
                this.filteredFeedbacks.sort((a, b) => (b.rating || 0) - (a.rating || 0));
                break;
            case 'rating-low':
                this.filteredFeedbacks.sort((a, b) => (a.rating || 0) - (b.rating || 0));
                break;
        }
    }

    displayFeedbacks() {
        const container = document.getElementById('feedbacksList');
        
        if (this.filteredFeedbacks.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-comment-dots"></i>
                    <p>No feedbacks found</p>
                    <p class="text-muted">Try adjusting your filters</p>
                </div>
            `;
            return;
        }

        const feedbacksHtml = this.filteredFeedbacks.map(feedback => this.createFeedbackCard(feedback)).join('');
        container.innerHTML = feedbacksHtml;
    }

    createFeedbackCard(feedback) {
        const ratingStars = this.getRatingStars(feedback.rating);
        const date = new Date(feedback.submitted_at).toLocaleDateString();
        
        return `
            <div class="feedback-card card mb-3">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <div>
                            <h6 class="card-title mb-1">
                                ${feedback.student_name}
                            </h6>
                            <small class="text-muted">${feedback.student_email} • ${date}</small>
                        </div>
                        <div class="text-end">
                            ${ratingStars}
                            <div class="mt-2">
                                <button class="btn btn-sm btn-outline-danger" onclick="deleteFeedback(${feedback.id})">
                                    <i class="fas fa-trash"></i> Delete
                                </button>
                            </div>
                        </div>
                    </div>
                    <p class="card-text">${feedback.feedback}</p>
                </div>
            </div>
        `;
    }

    getRatingStars(rating) {
        if (!rating) return '<span class="text-muted">No rating</span>';
        
        const stars = '⭐'.repeat(rating);
        const emptyStars = '☆'.repeat(5 - rating);
        return `<span class="rating-stars">${stars}${emptyStars}</span>`;
    }

    showDeleteModal(feedbackId) {
        document.getElementById('deleteFeedbackId').value = feedbackId;
        const modal = new bootstrap.Modal(document.getElementById('deleteFeedbackModal'));
        modal.show();
    }

    async confirmDeleteFeedback() {
        const feedbackId = document.getElementById('deleteFeedbackId').value;
        
        try {
            const response = await this.makeAuthenticatedRequest(`admin/feedback/${feedbackId}/`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.showAlert('Feedback deleted successfully!', 'success');
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('deleteFeedbackModal'));
                modal.hide();
                
                // Reload feedbacks
                this.loadFeedbacks();
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Failed to delete feedback');
            }
        } catch (error) {
            console.error('Error deleting feedback:', error);
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

// Initialize feedback management when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new FeedbackManagement();
});
