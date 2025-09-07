// static/js/app.js - Main application controller for Django
class DjangoApp {
    constructor() {
        this.API_BASE_URL = 'http://127.0.0.1:8000/api';
        this.authManager = new AuthManager(this.API_BASE_URL);
        this.uploadManager = new UploadManager(this.API_BASE_URL, this.authManager);
        this.isInitialized = false;
    }

    // Initialize the application
    async init() {
        if (this.isInitialized) return;

        this.setupEventListeners();
        this.uploadManager.init();
        await this.checkInitialAuthStatus();
        this.setupNavigation();
        this.isInitialized = true;
        
        console.log('Django App initialized successfully');
    }

    // Setup global event listeners
    setupEventListeners() {
        // Login form handler
        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => {
                this.handleLogin(e);
            });
        }

        // Logout button handler
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                this.handleLogout();
            });
        }

        // Reprocess button handler
        const reprocessBtn = document.querySelector('.action-buttons .btn');
        if (reprocessBtn && reprocessBtn.textContent.includes('Reprocess')) {
            reprocessBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.uploadManager.reprocessLatest();
            });
        }

        // Custom events from other modules
        window.addEventListener('authRequired', () => {
            this.showLoginSection();
            this.clearAllMessages();
        });

        window.addEventListener('uploadCompleted', () => {
            this.uploadManager.loadUploads();
        });

        // Mobile navigation toggle
        this.setupMobileNav();
    }

    // Setup mobile navigation
    setupMobileNav() {
        const navToggle = document.getElementById('navToggle');
        const navMenu = document.getElementById('navMenu');
        
        if (navToggle && navMenu) {
            navToggle.addEventListener('click', () => {
                navMenu.classList.toggle('active');
                navToggle.classList.toggle('active');
            });

            // Close mobile menu when clicking outside
            document.addEventListener('click', (e) => {
                if (!navToggle.contains(e.target) && !navMenu.contains(e.target)) {
                    navMenu.classList.remove('active');
                    navToggle.classList.remove('active');
                }
            });
        }
    }

    // Setup navigation buttons
    setupNavigation() {
        const loginNavBtn = document.getElementById('loginNavBtn');
        const registerNavBtn = document.getElementById('registerNavBtn');
        const loginSection = document.getElementById('loginSection');

        if (loginNavBtn && loginSection) {
            loginNavBtn.addEventListener('click', (e) => {
                e.preventDefault();
                loginSection.scrollIntoView({ behavior: 'smooth' });
                this.showLoginSection();
            });
        }

        if (registerNavBtn) {
            registerNavBtn.addEventListener('click', (e) => {
                e.preventDefault();
                // Handle registration if needed
                console.log('Register clicked');
            });
        }
    }

    // Check authentication status on app initialization
    async checkInitialAuthStatus() {
        const authStatus = await this.authManager.checkAuthStatus();
        
        if (authStatus.isAuthenticated) {
            this.showUploadSection();
            this.uploadManager.loadUploads();
            this.updateNavForAuthenticatedUser();
        } else {
            this.showLoginSection();
            this.updateNavForUnauthenticatedUser();
        }
    }

    // Handle login form submission
    async handleLogin(e) {
        e.preventDefault();
        this.clearAllMessages();

        const formData = new FormData(e.target);
        const email = formData.get('email');
        const password = formData.get('password');

        if (!email || !password) {
            this.showLoginMessage('Please fill in all fields', 'error');
            return;
        }

        // Show loading state
        const submitBtn = e.target.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Logging in...';
        submitBtn.disabled = true;

        try {
            const result = await this.authManager.login(email, password);
            
            this.showLoginMessage(result.message, result.success ? 'success' : 'error');

            if (result.success) {
                setTimeout(() => {
                    this.showUploadSection();
                    this.uploadManager.loadUploads();
                    this.updateNavForAuthenticatedUser();
                }, 1000);
            }
        } finally {
            // Restore button state
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    }

    // Handle logout
    async handleLogout() {
        try {
            await this.authManager.logout();
            this.showLoginSection();
            this.clearAllMessages();
            this.updateNavForUnauthenticatedUser();
            
            // Reset forms
            const loginForm = document.getElementById('loginForm');
            const uploadForm = document.getElementById('uploadForm');
            
            if (loginForm) loginForm.reset();
            if (uploadForm) uploadForm.reset();
            
            // Reset file input
            this.uploadManager.resetFileInput();
            
            this.showLoginMessage('Logged out successfully', 'success');
        } catch (err) {
            console.error('Logout error:', err);
        }
    }

    // UI State Management
    showLoginSection() {
        const loginSection = document.getElementById('loginSection');
        const uploadSection = document.getElementById('uploadSection');
        const uploadsList = document.getElementById('uploadsList');
        const logoutBtn = document.getElementById('logoutBtn');

        if (loginSection) loginSection.style.display = 'block';
        if (uploadSection) uploadSection.style.display = 'none';
        if (uploadsList) uploadsList.style.display = 'none';
        if (logoutBtn) logoutBtn.style.display = 'none';
    }

    showUploadSection() {
        const loginSection = document.getElementById('loginSection');
        const uploadSection = document.getElementById('uploadSection');
        const uploadsList = document.getElementById('uploadsList');
        const logoutBtn = document.getElementById('logoutBtn');

        if (loginSection) loginSection.style.display = 'none';
        if (uploadSection) uploadSection.style.display = 'block';
        if (uploadsList) uploadsList.style.display = 'block';
        if (logoutBtn) logoutBtn.style.display = 'block';
    }

    // Navigation state management
    updateNavForAuthenticatedUser() {
        const loginNavBtn = document.getElementById('loginNavBtn');
        const registerNavBtn = document.getElementById('registerNavBtn');
        const userInfo = this.authManager.getCurrentUserInfo();

        if (loginNavBtn && userInfo) {
            loginNavBtn.textContent = `Welcome, ${userInfo.email.split('@')[0]}`;
            loginNavBtn.style.pointerEvents = 'none';
        }
        
        if (registerNavBtn) {
            registerNavBtn.style.display = 'none';
        }
    }

    updateNavForUnauthenticatedUser() {
        const loginNavBtn = document.getElementById('loginNavBtn');
        const registerNavBtn = document.getElementById('registerNavBtn');

        if (loginNavBtn) {
            loginNavBtn.textContent = 'Login';
            loginNavBtn.style.pointerEvents = '';
        }
        
        if (registerNavBtn) {
            registerNavBtn.style.display = '';
        }
    }

    // Message Management
    showLoginMessage(message, type) {
        const container = document.getElementById('loginMessage');
        if (container) {
            container.innerHTML = `<div class="message ${type}">${message}</div>`;
            
            // Auto-hide success messages
            if (type === 'success') {
                setTimeout(() => {
                    container.innerHTML = '';
                }, 3000);
            }
        }
    }

    clearAllMessages() {
        ['loginMessage', 'uploadMessage'].forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.innerHTML = '';
            }
        });
    }

    // Public methods for external access
    async refreshAuth() {
        return await this.checkInitialAuthStatus();
    }

    getCurrentUser() {
        return this.authManager.getCurrentUserInfo();
    }

    // Utility method for smooth scrolling
    scrollToSection(sectionId) {
        const section = document.getElementById(sectionId);
        if (section) {
            section.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    // Handle page visibility changes
    handleVisibilityChange() {
        if (!document.hidden) {
            // Page is visible again, check auth status
            this.checkInitialAuthStatus();
        }
    }
}

// Global app instance and initialization
let djangoApp;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', async () => {
    djangoApp = new DjangoApp();
    await djangoApp.init();
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (djangoApp && djangoApp.isInitialized) {
        djangoApp.handleVisibilityChange();
    }
});

// Export app instance for external access
window.djangoApp = djangoApp;