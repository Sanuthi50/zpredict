// Index Page Manager - Similar to FeedbackManager pattern
class IndexPageManager {
    constructor() {
        this.apiBaseUrl = 'http://127.0.0.1:8000/api/';
        this.token = localStorage.getItem('access_token');
        this.init();
    }

    init() {
        this.setupParticles();
        this.setupNavigation();
        this.setupFeedbackSystem();
    }

    // Get authentication token
    getAuthToken() {
        return localStorage.getItem('access_token');
    }

    // Setup particle background effect
    setupParticles() {
        const particles = document.getElementById('particles');
        if (particles) {
            for (let i = 0; i < 50; i++) {
                const particle = document.createElement('div');
                particle.style.position = 'absolute';
                particle.style.width = Math.random() * 5 + 2 + 'px';
                particle.style.height = particle.style.width;
                particle.style.background = i % 3 === 0 ? '#6C63FF' : i % 3 === 1 ? '#36D6C3' : '#FF6B8B';
                particle.style.borderRadius = '50%';
                particle.style.opacity = Math.random() * 0.5 + 0.1;
                particle.style.top = Math.random() * 100 + 'vh';
                particle.style.left = Math.random() * 100 + 'vw';
                
                particles.appendChild(particle);
                this.animateParticle(particle);
            }
        }
    }

    animateParticle(particle) {
        const duration = Math.random() * 10 + 10;
        
        particle.animate([
            { transform: 'translateY(0px)', opacity: particle.style.opacity },
            { transform: `translateY(${Math.random() * 100 - 50}px) translateX(${Math.random() * 100 - 50}px)`, opacity: Math.random() * 0.5 }
        ], {
            duration: duration * 1000,
            iterations: Infinity,
            direction: 'alternate',
            easing: 'ease-in-out'
        });
    }

    // Setup navigation
    setupNavigation() {
        const navToggle = document.getElementById('navToggle');
        const navMenu = document.getElementById('navMenu');
        
        if (navToggle && navMenu) {
            navToggle.addEventListener('click', () => {
                navMenu.classList.toggle('active');
                navToggle.classList.toggle('active');
            });
        }

        // Close menu when clicking on a link (mobile)
        const navLinks = document.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', () => {
                if (navMenu) navMenu.classList.remove('active');
                if (navToggle) navToggle.classList.remove('active');
            });
        });
    }

    // Setup feedback system
    setupFeedbackSystem() {
        const feedbackForm = document.getElementById('feedbackForm');
        if (feedbackForm) {
            feedbackForm.addEventListener('submit', (e) => this.submitFeedback(e));
            this.loadFeedbacks();
        }
    }

    // Show alert messages
    showAlert(message, type = 'success') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" onclick="this.parentElement.remove()">×</button>
        `;
        document.body.appendChild(alertDiv);
        
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }

    // Load and display feedbacks
    async loadFeedbacks() {
        try {
            const token = this.getAuthToken();
            if (!token) {
                console.log('No auth token, showing empty state');
                this.displayFeedbacks([]);
                return;
            }

            console.log('Loading feedbacks with token:', token ? 'present' : 'missing');
            const response = await fetch(this.apiBaseUrl + 'feedback/', {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            
            console.log('Feedback response status:', response.status);
            if (response.ok) {
                const data = await response.json();
                console.log('Feedback data received:', data);
                console.log('Data keys:', Object.keys(data));
                console.log('Data type:', typeof data);
                
                // Try different possible data structures
                let feedbacks = [];
                if (Array.isArray(data)) {
                    feedbacks = data;
                } else if (data.feedbacks) {
                    feedbacks = data.feedbacks;
                } else if (data.results) {
                    feedbacks = data.results;
                } else if (data.data) {
                    feedbacks = data.data;
                }
                
                console.log('Extracted feedbacks:', feedbacks);
                console.log('Feedbacks count:', feedbacks.length);
                this.displayFeedbacks(feedbacks);
            } else {
                console.error('Failed to fetch feedbacks, status:', response.status);
                const errorText = await response.text();
                console.error('Error response:', errorText);
                this.displayFeedbacks([]);
            }
        } catch (error) {
            console.error('Error fetching feedbacks:', error);
            this.displayFeedbacks([]);
        }
    }

    // Display feedbacks in the UI
    displayFeedbacks(feedbacks) {
        const container = document.getElementById('recentFeedbacks');
        if (!container) return;
        
        if (!feedbacks || feedbacks.length === 0) {
            container.innerHTML = '<div class="empty-state">No feedbacks yet. Be the first to share!</div>';
            return;
        }
        
        const feedbacksHtml = feedbacks.slice(0, 5).map(feedback => {
            const stars = '⭐'.repeat(feedback.rating || 0);
            const date = new Date(feedback.submitted_at).toLocaleDateString();
            return `
                <div class="feedback-item">
                    <div class="feedback-header">
                        <strong>${feedback.student_name || 'Anonymous'}</strong>
                        <span class="feedback-rating">${stars}</span>
                        <small class="feedback-date">${date}</small>
                    </div>
                    <p class="feedback-text">${feedback.feedback}</p>
                </div>
            `;
        }).join('');
        
        container.innerHTML = feedbacksHtml;
    }

    // Submit feedback
    async submitFeedback(event) {
        event.preventDefault();
        
        const feedbackForm = document.getElementById('feedbackForm');
        const formData = new FormData(feedbackForm);
        const feedbackText = formData.get('feedback');
        const rating = formData.get('rating');
        
        if (!feedbackText.trim()) {
            this.showAlert('Please provide your feedback', 'error');
            return;
        }
        
        if (!rating) {
            this.showAlert('Please select a rating', 'error');
            return;
        }
        
        try {
            const token = this.getAuthToken();
            if (!token) {
                this.showAlert('Please log in to submit feedback', 'error');
                return;
            }

            const response = await fetch(this.apiBaseUrl + 'feedback/', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    feedback: feedbackText,
                    rating: parseInt(rating)
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to submit feedback');
            }
            
            const newFeedback = await response.json();
            this.showAlert('Thank you for your feedback!');
            feedbackForm.reset();
            
            // Refresh the feedback list
            this.loadFeedbacks();
            
        } catch (error) {
            console.error('Error submitting feedback:', error);
            this.showAlert(error.message || 'Failed to submit feedback. Please try again.', 'error');
        }
    }
}

// Global navigation function
function navigateTo(url) {
    window.location.href = url;
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new IndexPageManager();
});