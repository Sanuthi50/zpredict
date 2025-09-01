// Admin Dashboard JavaScript
class AdminDashboard {
    constructor() {
        this.apiBaseUrl = '/api/';
        this.token = localStorage.getItem('access_token'); // Admin tokens are stored as access_token
        this.adminInfo = JSON.parse(localStorage.getItem('admin_info') || localStorage.getItem('user_info') || '{}');
        this.currentChart = null;
        this.currentChartType = 'predictions';
        this.feedbackPage = 1;
        this.feedbackSearch = '';
        this.feedbackFilter = 'all';
        this.init();
    }

    async init() {
        await this.checkAuth();
        this.loadDashboardData();
        this.loadModelHealth();
        this.loadAnalytics();
        this.loadFeedbacks();
        this.loadRecentActivity();
        this.bindEvents();
        this.initParticles();
    }

    async checkAuth() {
        const loadingScreen = document.getElementById('loadingScreen');
        const mainContainer = document.querySelector('.main-container');
        
        if (!this.token) {
            this.redirectToLogin();
            return;
        }

        // Check if token is expired
        if (this.isTokenExpired()) {
            // Try refreshing token if refresh token exists
            const refreshToken = localStorage.getItem('refresh_token');
            if (refreshToken) {
                const refreshSuccess = await this.refreshAccessToken(refreshToken);
                if (refreshSuccess) {
                    this.token = localStorage.getItem('access_token');
                } else {
                    this.redirectToLogin();
                    return;
                }
            } else {
                this.redirectToLogin();
                return;
            }
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}admin/verify/`, {
                headers: {
                    'Authorization': `Bearer ${this.token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error('Authentication failed');
            }

            const userData = await response.json();
            // Admin verify endpoint should return admin user data

            this.adminInfo = userData;
            const adminNameEl = document.getElementById('adminName');
            if (adminNameEl) {
                adminNameEl.textContent = `${userData.first_name} ${userData.last_name}`;
            }
            
            // Show main content and hide loading screen
            if (loadingScreen) loadingScreen.style.display = 'none';
            if (mainContainer) mainContainer.classList.add('authenticated');
            
        } catch (error) {
            console.error('Auth check failed:', error);
            this.redirectToLogin();
        }
    }

    // Helper: Check if JWT is expired
    isTokenExpired() {
        const token = localStorage.getItem('access_token');
        if (!token) return true;
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            return payload.exp * 1000 < Date.now(); // Expired?
        } catch {
            return true;
        }
    }

    // Refresh access token
    async refreshAccessToken(refreshToken) {
        try {
            const res = await fetch(`${this.apiBaseUrl}token/refresh/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh: refreshToken })
            });

            if (res.ok) {
                const data = await res.json();
                localStorage.setItem('access_token', data.access);
                return true;
            } else {
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                return false;
            }
        } catch (err) {
            console.error("Token refresh failed:", err);
            return false;
        }
    }

    redirectToLogin() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('admin_token');
        localStorage.removeItem('admin_info');
        localStorage.removeItem('user_info');
        window.location.href = '/login/';
    }

    async loadDashboardData() {
        try {
            const response = await fetch(`${this.apiBaseUrl}admin/dashboard/`, {
                headers: {
                    'Authorization': `Bearer ${this.token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error('Failed to load dashboard data');
            }

            const data = await response.json();
            this.updateStatistics(data.stats);
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.showToast('Error loading dashboard data', 'error');
        }
    }

    updateStatistics(stats) {
        document.getElementById('totalStudents').textContent = stats.total_students || 0;
        document.getElementById('totalAdmins').textContent = stats.total_admins || 0;
        document.getElementById('totalPredictions').textContent = stats.total_predictions || 0;
        document.getElementById('totalCareerRecommendations').textContent = stats.total_career_sessions || 0;
        document.getElementById('totalChats').textContent = stats.total_chats || 0;
        document.getElementById('totalFeedbacks').textContent = stats.total_feedbacks || 0;
    }

    async loadModelHealth() {
        try {
            const response = await fetch(`${this.apiBaseUrl}models/status/`, {
                headers: {
                    'Authorization': `Bearer ${this.token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error('Failed to load model health');
            }

            const data = await response.json();
            this.renderModelHealth(data);
        } catch (error) {
            console.error('Error loading model health:', error);
            this.showToast('Error loading model health', 'error');
        }
    }

    renderModelHealth(data) {
        const grid = document.getElementById('modelHealthGrid');
        
        const modelCards = [
            {
                title: 'ML Prediction Models',
                icon: 'fas fa-brain',
                status: data.models?.ml_prediction_models?.models_loaded ? 'healthy' : 'error',
                details: data.models?.ml_prediction_models || {}
            },
            {
                title: 'Career Prediction Models',
                icon: 'fas fa-rocket',
                status: data.models?.career_prediction_models?.models_loaded ? 'healthy' : 'error',
                details: data.models?.career_prediction_models || {}
            },
            {
                title: 'Embeddings Model',
                icon: 'fas fa-layer-group',
                status: data.models?.embeddings_loaded ? 'healthy' : 'error',
                details: { 'Loaded': data.models?.embeddings_loaded }
            },
            {
                title: 'LLM Model',
                icon: 'fas fa-robot',
                status: data.models?.llm_loaded ? 'healthy' : 'error',
                details: { 'Loaded': data.models?.llm_loaded }
            },
            {
                title: 'Vector Stores',
                icon: 'fas fa-database',
                status: data.models?.vectorstore_count > 0 ? 'healthy' : 'warning',
                details: { 'Count': data.models?.vectorstore_count || 0 }
            },
            {
                title: 'Celery Worker',
                icon: 'fas fa-cogs',
                status: data.uploads?.celery_worker_healthy ? 'healthy' : 'error',
                details: { 'Healthy': data.uploads?.celery_worker_healthy }
            }
        ];

        grid.innerHTML = modelCards.map(card => `
            <div class="model-status-card">
                <div class="model-status-header">
                    <div class="model-status-icon ${card.status}">
                        <i class="${card.icon}"></i>
                    </div>
                    <h4 class="model-status-title">${card.title}</h4>
                </div>
                <div class="model-status-details">
                    ${Object.entries(card.details).map(([key, value]) => `
                        <div class="status-item">
                            <span class="status-label">${key}</span>
                            <span class="status-value ${value === true ? 'true' : value === false ? 'false' : ''}">${value}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('');
    }

    async loadAnalytics() {
        try {
            console.log('Loading analytics data...');
            
            const [predictionsData, careersData, usersData] = await Promise.all([
                this.fetchAnalyticsData('predictions'),
                this.fetchAnalyticsData('careers'),
                this.fetchAnalyticsData('users')
            ]);

            console.log('Analytics data received:', {
                predictions: predictionsData,
                careers: careersData,
                users: usersData
            });

            this.analyticsData = {
                predictions: predictionsData,
                careers: careersData,
                users: usersData
            };

            this.renderChart('predictions');
            this.updateAnalyticsSummary();
        } catch (error) {
            console.error('Error loading analytics:', error);
            this.showToast('Error loading analytics', 'error');
            
            // Set default empty data to prevent undefined errors
            this.analyticsData = {
                predictions: { top_universities: [], popular_courses: [], labels: [], values: [] },
                careers: { top_careers: [], labels: [], values: [] },
                users: { labels: [], values: [] }
            };
            this.updateAnalyticsSummary();
        }
    }

    async fetchAnalyticsData(type) {
        console.log(`Fetching ${type} analytics...`);
        
        const response = await fetch(`${this.apiBaseUrl}admin/analytics/${type}/`, {
            headers: {
                'Authorization': `Bearer ${this.token}`,
                'Content-Type': 'application/json'
            }
        });

        console.log(`${type} analytics response status:`, response.status);

        if (!response.ok) {
            const errorText = await response.text();
            console.error(`${type} analytics error:`, errorText);
            throw new Error(`Failed to load ${type} analytics: ${response.status} - ${errorText}`);
        }

        const data = await response.json();
        console.log(`${type} analytics data:`, data);
        return data;
    }

    renderChart(type) {
        const ctx = document.getElementById('analyticsChart');
        
        if (this.currentChart) {
            this.currentChart.destroy();
        }

        const data = this.analyticsData[type];
        if (!data) return;

        this.currentChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels || [],
                datasets: [{
                    label: data.label || type.charAt(0).toUpperCase() + type.slice(1),
                    data: data.values || [],
                    backgroundColor: 'rgba(108, 99, 255, 0.8)',
                    borderColor: 'rgba(108, 99, 255, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    updateAnalyticsSummary() {
        console.log('Analytics data:', this.analyticsData);
        
        // Update top universities
        const topUniversities = document.getElementById('topUniversities');
        if (this.analyticsData.predictions?.top_universities && this.analyticsData.predictions.top_universities.length > 0) {
            topUniversities.innerHTML = this.analyticsData.predictions.top_universities
                .map(uni => `
                    <div class="summary-item">
                        <span class="summary-label">${uni.name || 'Unknown University'}</span>
                        <span class="summary-count">${uni.count || 0}</span>
                    </div>
                `).join('');
        } else {
            topUniversities.innerHTML = `
                <div class="summary-item">
                    <span class="summary-label">No data available</span>
                    <span class="summary-count">0</span>
                </div>
            `;
        }

        // Update popular courses
        const popularCourses = document.getElementById('popularCourses');
        if (this.analyticsData.predictions?.popular_courses && this.analyticsData.predictions.popular_courses.length > 0) {
            popularCourses.innerHTML = this.analyticsData.predictions.popular_courses
                .map(course => `
                    <div class="summary-item">
                        <span class="summary-label">${course.name || 'Unknown Course'}</span>
                        <span class="summary-count">${course.count || 0}</span>
                    </div>
                `).join('');
        } else {
            popularCourses.innerHTML = `
                <div class="summary-item">
                    <span class="summary-label">No data available</span>
                    <span class="summary-count">0</span>
                </div>
            `;
        }

        // Update top careers
        const topCareers = document.getElementById('topCareers');
        if (this.analyticsData.careers?.top_careers && this.analyticsData.careers.top_careers.length > 0) {
            topCareers.innerHTML = this.analyticsData.careers.top_careers
                .map(career => `
                    <div class="summary-item">
                        <span class="summary-label">${career.title || 'Unknown Career'}</span>
                        <span class="summary-count">${career.count || 0}</span>
                    </div>
                `).join('');
        } else {
            topCareers.innerHTML = `
                <div class="summary-item">
                    <span class="summary-label">No data available</span>
                    <span class="summary-count">0</span>
                </div>
            `;
        }
    }

    async loadFeedbacks() {
        try {
            // Simplified request without problematic parameters
            let url = `${this.apiBaseUrl}feedback/`;
            
            // Only add search if it exists and is not empty
            if (this.feedbackSearch && this.feedbackSearch.trim()) {
                url += `?search=${encodeURIComponent(this.feedbackSearch.trim())}`;
            }

            const response = await fetch(url, {
                headers: {
                    'Authorization': `Bearer ${this.token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                console.error('Feedback API error:', response.status, errorData);
                throw new Error(`Failed to load feedbacks: ${response.status} - ${errorData.detail || errorData.error || 'Unknown error'}`);
            }

            const data = await response.json();
            this.renderFeedbacks(data.results || data);
            this.renderFeedbackPagination(data);
        } catch (error) {
            console.error('Error loading feedbacks:', error);
            this.showToast('Error loading feedbacks', 'error');
            
            // Show empty state on error
            const container = document.getElementById('feedbackList');
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">⚠️</div>
                    <h3>Error loading feedback</h3>
                    <p>Unable to load feedback data. Please try again later.</p>
                </div>
            `;
        }
    }

    renderFeedbacks(feedbacks) {
        const container = document.getElementById('feedbackList');
        
        if (feedbacks.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">💭</div>
                    <h3>No feedback found</h3>
                    <p>No feedback matches your search criteria.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = feedbacks.map(feedback => `
            <div class="feedback-item" data-feedback-id="${feedback.id}">
                <div class="feedback-header">
                    <div class="feedback-meta">
                        <div class="feedback-user">${feedback.student_name}</div>
                        <div class="feedback-date">${new Date(feedback.submitted_at).toLocaleDateString('en-US', {
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                        })}</div>
                    </div>
                    <div class="feedback-rating">
                        <span>Rating:</span>
                        <div class="rating-stars">
                            ${this.generateStars(feedback.rating)}
                        </div>
                    </div>
                </div>
                <div class="feedback-text">${feedback.feedback}</div>
                <div class="feedback-actions">
                    <button class="btn btn-danger delete-feedback-btn" data-feedback-id="${feedback.id}">Delete</button>
                </div>
            </div>
        `).join('');

        // Bind delete events
        document.querySelectorAll('.delete-feedback-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const feedbackId = e.target.dataset.feedbackId;
                this.deleteFeedback(feedbackId);
            });
        });
    }

    generateStars(rating) {
        const stars = [];
        for (let i = 1; i <= 5; i++) {
            stars.push(`<span class="star">${i <= rating ? '★' : '☆'}</span>`);
        }
        return stars.join('');
    }

    async deleteFeedback(feedbackId) {
        this.showConfirmationModal(
            'Delete Feedback',
            'Are you sure you want to delete this feedback? This action cannot be undone.',
            async () => {
                try {
                    const response = await fetch(`${this.apiBaseUrl}feedback/${feedbackId}/`, {
                        method: 'DELETE',
                        headers: {
                            'Authorization': `Bearer ${this.token}`,
                            'Content-Type': 'application/json'
                        }
                    });

                    if (!response.ok) {
                        throw new Error('Failed to delete feedback');
                    }

                    this.showToast('Feedback deleted successfully', 'success');
                    this.loadFeedbacks();
                } catch (error) {
                    console.error('Failed to delete feedback:', error);
                    this.showToast('Failed to delete feedback', 'error');
                }
            }
        );
    }

    renderFeedbackPagination(data) {
        const pagination = document.getElementById('feedbackPagination');
        
        if (!data.count || data.count <= 10) {
            pagination.innerHTML = '';
            return;
        }

        const totalPages = Math.ceil(data.count / 10);
        const currentPage = this.feedbackPage;

        let paginationHTML = '';
        
        // Previous button
        paginationHTML += `
            <button class="pagination-btn" ${currentPage === 1 ? 'disabled' : ''} data-page="${currentPage - 1}">
                Previous
            </button>
        `;

        // Page numbers
        for (let i = Math.max(1, currentPage - 2); i <= Math.min(totalPages, currentPage + 2); i++) {
            paginationHTML += `
                <button class="pagination-btn ${i === currentPage ? 'active' : ''}" data-page="${i}">
                    ${i}
                </button>
            `;
        }

        // Next button
        paginationHTML += `
            <button class="pagination-btn" ${currentPage === totalPages ? 'disabled' : ''} data-page="${currentPage + 1}">
                Next
            </button>
        `;

        pagination.innerHTML = paginationHTML;

        // Bind pagination events
        pagination.querySelectorAll('.pagination-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const page = parseInt(e.target.dataset.page);
                if (page && page !== currentPage) {
                    this.feedbackPage = page;
                    this.loadFeedbacks();
                }
            });
        });
    }

    async loadRecentActivity() {
        try {
            const [predictions, careers, users] = await Promise.all([
                this.fetchRecentData('saved-predictions'),
                this.fetchRecentData('career-predictions'),
                this.fetchRecentData('users')
            ]);

            this.renderRecentActivity('recentPredictions', predictions, 'predictions');
            this.renderRecentActivity('recentCareers', careers, 'careers');
            this.renderRecentActivity('recentUsers', users, 'users');
        } catch (error) {
            console.error('Error loading recent activity:', error);
            this.showToast('Error loading recent activity', 'error');
        }
    }

    async fetchRecentData(type) {
        const response = await fetch(`${this.apiBaseUrl}${type}/?limit=5`, {
            headers: {
                'Authorization': `Bearer ${this.token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`Failed to load recent ${type}`);
        }

        return await response.json();
    }

    renderRecentActivity(containerId, data, type) {
        const container = document.getElementById(containerId);
        
        if (!data || data.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>No recent ${type} activity</p>
                </div>
            `;
            return;
        }

        const items = data.map(item => {
            switch (type) {
                case 'predictions':
                    return `
                        <div class="activity-item">
                            <div class="activity-icon">
                                <i class="fas fa-university"></i>
                            </div>
                            <div class="activity-content">
                                <div class="activity-title">${item.course_name}</div>
                                <div class="activity-meta">${item.university_name} • ${new Date(item.saved_at).toLocaleDateString()}</div>
                            </div>
                        </div>
                    `;
                case 'careers':
                    return `
                        <div class="activity-item">
                            <div class="activity-icon">
                                <i class="fas fa-rocket"></i>
                            </div>
                            <div class="activity-content">
                                <div class="activity-title">${item.career_title}</div>
                                <div class="activity-meta">${item.career_code} • ${new Date(item.saved_at).toLocaleDateString()}</div>
                            </div>
                        </div>
                    `;
                case 'users':
                    return `
                        <div class="activity-item">
                            <div class="activity-icon">
                                <i class="fas fa-user"></i>
                            </div>
                            <div class="activity-content">
                                <div class="activity-title">${item.first_name} ${item.last_name}</div>
                                <div class="activity-meta">${item.email} • ${new Date(item.date_joined).toLocaleDateString()}</div>
                            </div>
                        </div>
                    `;
                default:
                    return '';
            }
        }).join('');

        container.innerHTML = items;
    }

    bindEvents() {
        // Chart controls
        document.querySelectorAll('.chart-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.chart-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                
                const chartType = e.target.dataset.chart;
                this.currentChartType = chartType;
                this.renderChart(chartType);
            });
        });

        // Model health refresh
        document.getElementById('refreshModelHealth').addEventListener('click', () => {
            this.loadModelHealth();
        });

        // Feedback search and filter
        document.getElementById('feedbackSearch').addEventListener('input', (e) => {
            this.feedbackSearch = e.target.value;
            this.feedbackPage = 1;
            this.loadFeedbacks();
        });

        document.getElementById('feedbackFilter').addEventListener('change', (e) => {
            this.feedbackFilter = e.target.value;
            this.feedbackPage = 1;
            this.loadFeedbacks();
        });

        // Logout
        document.getElementById('logoutBtn').addEventListener('click', () => {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('admin_token');
            localStorage.removeItem('admin_info');
            localStorage.removeItem('user_info');
            window.location.href = '/login/';
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
    new AdminDashboard();
});
