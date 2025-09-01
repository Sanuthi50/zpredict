// Student Profile JavaScript
class StudentProfile {
    constructor() {
        this.currentUser = null;
        this.feedbacks = [];
        this.init();
    }

    async init() {
        await this.checkAuth();
        this.loadUserData();
        this.loadFeedbacks();
        this.bindEvents();
        this.initParticles();
    }

    async checkAuth() {
        const token = localStorage.getItem('access_token');
        if (!token) {
            window.location.href = '/website/login/';
            return;
        }

        try {
            const response = await fetch('/api/auth/me/', {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error('Authentication failed');
            }

            this.currentUser = await response.json();
        } catch (error) {
            console.error('Auth check failed:', error);
            localStorage.removeItem('access_token');
            window.location.href = '/website/login/';
        }
    }

    loadUserData() {
        if (!this.currentUser) return;

        // Display user information
        document.getElementById('firstNameDisplay').textContent = this.currentUser.first_name || 'Not set';
        document.getElementById('lastNameDisplay').textContent = this.currentUser.last_name || 'Not set';
        document.getElementById('emailDisplay').textContent = this.currentUser.email || 'Not set';
        
        const memberSince = new Date(this.currentUser.date_joined);
        document.getElementById('memberSinceDisplay').textContent = memberSince.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });

        // Populate edit form
        document.getElementById('editFirstName').value = this.currentUser.first_name || '';
        document.getElementById('editLastName').value = this.currentUser.last_name || '';
        document.getElementById('editEmail').value = this.currentUser.email || '';
    }

    async loadFeedbacks() {
        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch('/api/feedback/my_feedback/', {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error('Failed to load feedbacks');
            }

            this.feedbacks = await response.json();
            this.renderFeedbacks();
        } catch (error) {
            console.error('Failed to load feedbacks:', error);
            this.showToast('Failed to load feedbacks', 'error');
        }
    }

    renderFeedbacks() {
        const feedbackList = document.getElementById('feedbackList');
        
        if (this.feedbacks.length === 0) {
            feedbackList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">💭</div>
                    <h3>No feedback yet</h3>
                    <p>Share your thoughts about Zpredict to help us improve!</p>
                </div>
            `;
            return;
        }

        feedbackList.innerHTML = this.feedbacks.map(feedback => `
            <div class="feedback-item" data-feedback-id="${feedback.id}">
                <div class="feedback-header">
                    <div class="feedback-meta">
                        <div class="feedback-date">${new Date(feedback.submitted_at).toLocaleDateString('en-US', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                        })}</div>
                        <div class="feedback-rating">
                            <span>Rating:</span>
                            <div class="rating-stars">
                                ${this.generateStars(feedback.rating)}
                            </div>
                        </div>
                    </div>
                    <div class="feedback-actions">
                        <button class="btn btn-secondary edit-feedback-btn" data-feedback-id="${feedback.id}">Edit</button>
                        <button class="btn btn-danger delete-feedback-btn" data-feedback-id="${feedback.id}">Delete</button>
                    </div>
                </div>
                <div class="feedback-text">${feedback.feedback}</div>
            </div>
        `).join('');

        // Bind feedback action events
        this.bindFeedbackEvents();
    }

    generateStars(rating) {
        const stars = [];
        for (let i = 1; i <= 5; i++) {
            stars.push(`<span class="star">${i <= rating ? '★' : '☆'}</span>`);
        }
        return stars.join('');
    }

    bindFeedbackEvents() {
        // Edit feedback buttons
        document.querySelectorAll('.edit-feedback-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const feedbackId = e.target.dataset.feedbackId;
                this.editFeedback(feedbackId);
            });
        });

        // Delete feedback buttons
        document.querySelectorAll('.delete-feedback-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const feedbackId = e.target.dataset.feedbackId;
                this.deleteFeedback(feedbackId);
            });
        });
    }

    editFeedback(feedbackId) {
        const feedback = this.feedbacks.find(f => f.id == feedbackId);
        if (!feedback) return;

        // Populate the add feedback form for editing
        document.getElementById('feedbackText').value = feedback.feedback;
        document.getElementById('feedbackRating').value = feedback.rating;
        
        // Show the form and change button text
        document.getElementById('addFeedbackForm').style.display = 'block';
        document.getElementById('newFeedbackForm').dataset.editId = feedbackId;
        document.querySelector('#addFeedbackForm .btn-primary').textContent = 'Update Feedback';
        
        // Scroll to the form
        document.getElementById('addFeedbackForm').scrollIntoView({ behavior: 'smooth' });
    }

    async deleteFeedback(feedbackId) {
        this.showConfirmationModal(
            'Delete Feedback',
            'Are you sure you want to delete this feedback? This action cannot be undone.',
            async () => {
                try {
                    const token = localStorage.getItem('access_token');
                    const response = await fetch(`/api/feedback/${feedbackId}/`, {
                        method: 'DELETE',
                        headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json'
                        }
                    });

                    if (!response.ok) {
                        throw new Error('Failed to delete feedback');
                    }

                    this.showToast('Feedback deleted successfully', 'success');
                    await this.loadFeedbacks();
                } catch (error) {
                    console.error('Failed to delete feedback:', error);
                    this.showToast('Failed to delete feedback', 'error');
                }
            }
        );
    }

    bindEvents() {
        // Personal information edit
        document.getElementById('editPersonalBtn').addEventListener('click', () => {
            document.getElementById('personalEditForm').style.display = 'block';
        });

        document.getElementById('cancelPersonalBtn').addEventListener('click', () => {
            document.getElementById('personalEditForm').style.display = 'none';
        });

        document.getElementById('updatePersonalForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.updatePersonalInfo();
        });

        // Password change
        document.getElementById('changePasswordForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.changePassword();
        });

        // Feedback management
        document.getElementById('addFeedbackBtn').addEventListener('click', () => {
            document.getElementById('addFeedbackForm').style.display = 'block';
            document.getElementById('newFeedbackForm').reset();
            delete document.getElementById('newFeedbackForm').dataset.editId;
            document.querySelector('#addFeedbackForm .btn-primary').textContent = 'Submit Feedback';
        });

        document.getElementById('cancelFeedbackBtn').addEventListener('click', () => {
            document.getElementById('addFeedbackForm').style.display = 'none';
        });

        document.getElementById('newFeedbackForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitFeedback();
        });

        // Quick actions
        document.getElementById('viewChatHistoryBtn').addEventListener('click', () => {
            window.location.href = '/website/chat-history/';
        });

        document.getElementById('viewPredictionsBtn').addEventListener('click', () => {
            window.location.href = '/website/all-predictions/';
        });

        document.getElementById('viewCareerBtn').addEventListener('click', () => {
            window.location.href = '/website/career-predictions/';
        });

        // Account management
        document.getElementById('deactivateAccountBtn').addEventListener('click', () => {
            this.deactivateAccount();
        });

        document.getElementById('deleteAccountBtn').addEventListener('click', () => {
            this.deleteAccount();
        });

        // Modal events
        document.getElementById('modalClose').addEventListener('click', () => {
            this.hideModal();
        });

        document.getElementById('modalCancel').addEventListener('click', () => {
            this.hideModal();
        });

        // Close modal when clicking outside
        document.getElementById('confirmationModal').addEventListener('click', (e) => {
            if (e.target.id === 'confirmationModal') {
                this.hideModal();
            }
        });
    }

    async updatePersonalInfo() {
        const formData = new FormData(document.getElementById('updatePersonalForm'));
        const data = {
            first_name: formData.get('first_name'),
            last_name: formData.get('last_name'),
            email: formData.get('email')
        };

        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch('/api/auth/update-profile/', {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to update profile');
            }

            const updatedUser = await response.json();
            this.currentUser = updatedUser;
            this.loadUserData();
            document.getElementById('personalEditForm').style.display = 'none';
            this.showToast('Profile updated successfully', 'success');
        } catch (error) {
            console.error('Failed to update profile:', error);
            this.showToast(error.message || 'Failed to update profile', 'error');
        }
    }

    async changePassword() {
        const formData = new FormData(document.getElementById('changePasswordForm'));
        const newPassword = formData.get('new_password');
        const confirmPassword = formData.get('confirm_password');

        if (newPassword !== confirmPassword) {
            this.showToast('New passwords do not match', 'error');
            return;
        }

        const data = {
            current_password: formData.get('current_password'),
            new_password: newPassword
        };

        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch('/api/auth/change-password/', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to change password');
            }

            document.getElementById('changePasswordForm').reset();
            this.showToast('Password changed successfully', 'success');
        } catch (error) {
            console.error('Failed to change password:', error);
            this.showToast(error.message || 'Failed to change password', 'error');
        }
    }

    async submitFeedback() {
        const formData = new FormData(document.getElementById('newFeedbackForm'));
        const editId = document.getElementById('newFeedbackForm').dataset.editId;
        
        const data = {
            feedback: formData.get('feedback'),
            rating: parseInt(formData.get('rating'))
        };

        try {
            const token = localStorage.getItem('access_token');
            const url = editId ? `/api/feedback/${editId}/` : '/api/feedback/';
            const method = editId ? 'PUT' : 'POST';

            const response = await fetch(url, {
                method: method,
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to submit feedback');
            }

            document.getElementById('addFeedbackForm').style.display = 'none';
            document.getElementById('newFeedbackForm').reset();
            delete document.getElementById('newFeedbackForm').dataset.editId;
            
            const message = editId ? 'Feedback updated successfully' : 'Feedback submitted successfully';
            this.showToast(message, 'success');
            
            await this.loadFeedbacks();
        } catch (error) {
            console.error('Failed to submit feedback:', error);
            this.showToast(error.message || 'Failed to submit feedback', 'error');
        }
    }

    deactivateAccount() {
        this.showConfirmationModal(
            'Deactivate Account',
            'Your account will be temporarily deactivated. You can reactivate it by logging in again. Are you sure?',
            async () => {
                try {
                    const token = localStorage.getItem('access_token');
                    const response = await fetch('/api/auth/deactivate-account/', {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json'
                        }
                    });

                    if (!response.ok) {
                        throw new Error('Failed to deactivate account');
                    }

                    this.showToast('Account deactivated successfully', 'success');
                    setTimeout(() => {
                        localStorage.removeItem('access_token');
                        window.location.href = '/website/login/';
                    }, 2000);
                } catch (error) {
                    console.error('Failed to deactivate account:', error);
                    this.showToast('Failed to deactivate account', 'error');
                }
            }
        );
    }

    deleteAccount() {
        this.showConfirmationModal(
            'Delete Account',
            'This action cannot be undone. All your data will be permanently deleted. Are you absolutely sure?',
            async () => {
                try {
                    const token = localStorage.getItem('access_token');
                    const response = await fetch('/api/auth/delete-account/', {
                        method: 'DELETE',
                        headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json'
                        }
                    });

                    if (!response.ok) {
                        throw new Error('Failed to delete account');
                    }

                    this.showToast('Account deleted successfully', 'success');
                    setTimeout(() => {
                        localStorage.removeItem('access_token');
                        window.location.href = '/website/';
                    }, 2000);
                } catch (error) {
                    console.error('Failed to delete account:', error);
                    this.showToast('Failed to delete account', 'error');
                }
            }
        );
    }

    showConfirmationModal(title, message, onConfirm) {
        document.getElementById('modalTitle').textContent = title;
        document.getElementById('modalMessage').textContent = message;
        document.getElementById('modalConfirm').onclick = () => {
            this.hideModal();
            onConfirm();
        };
        document.getElementById('confirmationModal').classList.add('active');
    }

    hideModal() {
        document.getElementById('confirmationModal').classList.remove('active');
    }

    showToast(message, type = 'info') {
        const toast = document.getElementById('toast');
        const toastMessage = document.getElementById('toastMessage');
        
        toast.className = `toast ${type}`;
        toastMessage.textContent = message;
        toast.classList.add('show');
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 5000);
    }

    initParticles() {
        const particles = document.getElementById('particles');
        if (!particles) return;

        // Create animated particles
        for (let i = 0; i < 20; i++) {
            const particle = document.createElement('div');
            particle.style.cssText = `
                position: absolute;
                width: 4px;
                height: 4px;
                background: rgba(108, 99, 255, 0.3);
                border-radius: 50%;
                animation: float ${3 + Math.random() * 4}s ease-in-out infinite;
                left: ${Math.random() * 100}%;
                animation-delay: ${Math.random() * 2}s;
            `;
            particles.appendChild(particle);
        }

        // Add floating animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes float {
                0%, 100% { transform: translateY(0px) rotate(0deg); opacity: 0.3; }
                50% { transform: translateY(-20px) rotate(180deg); opacity: 0.8; }
            }
        `;
        document.head.appendChild(style);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new StudentProfile();
});
