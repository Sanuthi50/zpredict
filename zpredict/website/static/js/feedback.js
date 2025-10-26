// Feedback System JavaScript
class FeedbackManager {
    constructor() {
        this.apiBaseUrl = '/api/';
        this.token = localStorage.getItem('access_token');
        this.userInfo = JSON.parse(localStorage.getItem('user_info') || '{}');
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

        // Update user name in navigation
        if (this.userInfo.first_name) {
            document.getElementById('userName').textContent = `${this.userInfo.first_name} ${this.userInfo.last_name}`;
        }
    }

    setupEventListeners() {
        // Feedback form submission
        document.getElementById('feedbackForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitFeedback();
        });

        // Tab switching
        document.getElementById('all-tab').addEventListener('click', () => {
            this.loadAllFeedbacks();
        });

        document.getElementById('my-tab').addEventListener('click', () => {
            this.loadMyFeedbacks();
        });

        // Logout functionality
        window.logout = () => this.logout();
    }

    async loadFeedbacks() {
        await this.loadAllFeedbacks();
        await this.loadMyFeedbacks();
    }

    async loadAllFeedbacks() {
        try {
            const response = await this.makeAuthenticatedRequest('feedback/');
            if (response.ok) {
                const data = await response.json();
                this.displayAllFeedbacks(data.feedbacks);
            } else {
                throw new Error('Failed to load feedbacks');
            }
        } catch (error) {
            console.error('Error loading all feedbacks:', error);
            this.showAlert('Error loading feedbacks', 'danger');
        }
    }

    async loadMyFeedbacks() {
        try {
            const response = await this.makeAuthenticatedRequest('feedback/user/');
            if (response.ok) {
                const data = await response.json();
                this.displayMyFeedbacks(data.user_feedbacks);
            } else {
                throw new Error('Failed to load user feedbacks');
            }
        } catch (error) {
            console.error('Error loading user feedbacks:', error);
            this.showAlert('Error loading your feedbacks', 'danger');
        }
    }

    displayAllFeedbacks(feedbacks) {
        const container = document.getElementById('allFeedbacks');
        
        if (!feedbacks || feedbacks.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-comment-dots"></i>
                    <p>No feedbacks yet</p>
                    <p class="text-muted">Be the first to share your thoughts!</p>
                </div>
            `;
            return;
        }

        const feedbacksHtml = feedbacks.map(feedback => this.createFeedbackCard(feedback, false)).join('');
        container.innerHTML = feedbacksHtml;
    }

    displayMyFeedbacks(feedbacks) {
        const container = document.getElementById('myFeedbacks');
        
        if (!feedbacks || feedbacks.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-user"></i>
                    <p>You haven't submitted any feedback yet</p>
                    <p class="text-muted">Share your thoughts to help us improve!</p>
                </div>
            `;
            return;
        }

        const feedbacksHtml = feedbacks.map(feedback => this.createFeedbackCard(feedback, true)).join('');
        container.innerHTML = feedbacksHtml;
    }

    createFeedbackCard(feedback, isOwnFeedback) {
        const ratingStars = this.getRatingStars(feedback.rating);
        const date = new Date(feedback.submitted_at).toLocaleDateString();
        
        return `
            <div class="feedback-card card mb-3">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <div>
                            <h6 class="card-title mb-1">
                                ${feedback.student_name || 'Anonymous'}
                            </h6>
                            <small class="text-muted">${date}</small>
                        </div>
                        <div class="text-end">
                            ${ratingStars}
                            ${isOwnFeedback ? `
                                <div class="mt-2">
                                    <button class="btn btn-sm btn-outline-primary me-1" onclick="editFeedback(${feedback.id})">
                                        <i class="fas fa-edit"></i> Edit
                                    </button>
                                    <button class="btn btn-sm btn-outline-danger" onclick="deleteFeedback(${feedback.id})">
                                        <i class="fas fa-trash"></i> Delete
                                    </button>
                                </div>
                            ` : ''}
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

    async submitFeedback() {
        const feedbackText = document.getElementById('feedbackText').value.trim();
        const rating = document.getElementById('feedbackRating').value;

        if (!feedbackText) {
            this.showAlert('Please enter your feedback', 'warning');
            return;
        }

        try {
            const response = await this.makeAuthenticatedRequest('feedback/', {
                method: 'POST',
                body: JSON.stringify({
                    feedback: feedbackText,
                    rating: rating || null
                })
            });

            if (response.ok) {
                this.showAlert('Feedback submitted successfully!', 'success');
                document.getElementById('feedbackForm').reset();
                this.loadFeedbacks(); // Reload feedbacks
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Failed to submit feedback');
            }
        } catch (error) {
            console.error('Error submitting feedback:', error);
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
}

// Global functions for feedback operations
window.editFeedback = async function(feedbackId) {
    // Simple edit functionality - you can enhance this with a modal
    const newText = prompt('Edit your feedback:');
    if (newText === null) return; // User cancelled

    try {
        const response = await fetch(`/api/feedback/${feedbackId}/`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                feedback: newText
            })
        });

        if (response.ok) {
            // Reload feedbacks
            const feedbackManager = new FeedbackManager();
            feedbackManager.loadFeedbacks();
            feedbackManager.showAlert('Feedback updated successfully!', 'success');
        } else {
            const error = await response.json();
            throw new Error(error.error || 'Failed to update feedback');
        }
    } catch (error) {
        console.error('Error updating feedback:', error);
        alert(error.message);
    }
};

window.deleteFeedback = function(feedbackId) {
    if (!confirm('Are you sure you want to delete this feedback? This action cannot be undone.')) {
        return;
    }

    fetch(`/api/feedback/${feedbackId}/`, {
        method: 'DELETE',
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
        }
    })
    .then(response => {
        if (response.ok) {
            // Reload feedbacks
            const feedbackManager = new FeedbackManager();
            feedbackManager.loadFeedbacks();
            feedbackManager.showAlert('Feedback deleted successfully!', 'success');
        } else {
            throw new Error('Failed to delete feedback');
        }
    })
    .catch(error => {
        console.error('Error deleting feedback:', error);
        alert('Error deleting feedback');
    });
};

// Initialize feedback manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new FeedbackManager();
});
