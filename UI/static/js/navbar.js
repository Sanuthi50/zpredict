// Navbar Component JavaScript
class NavbarManager {
    constructor() {
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkAuthStatus();
        this.setActiveNavLink();
    }

    setupEventListeners() {
        // Mobile navigation toggle
        const navToggle = document.getElementById('navToggle');
        const navMenu = document.getElementById('navMenu');
        
        if (navToggle && navMenu) {
            navToggle.addEventListener('click', () => {
                navMenu.classList.toggle('active');
                navToggle.classList.toggle('active');
            });
        }

        // Logout functionality
        const logoutBtn = document.getElementById('logoutNavBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.logout();
            });
        }

        // Close mobile menu when clicking on nav links
        const navLinks = document.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', () => {
                if (navMenu.classList.contains('active')) {
                    navMenu.classList.remove('active');
                    navToggle.classList.remove('active');
                }
            });
        });
    }

    async checkAuthStatus() {
        const token = localStorage.getItem('access_token');
        const authButtons = document.getElementById('authButtons');
        const userMenu = document.getElementById('userMenu');
        const userName = document.getElementById('userName');

        if (!token) {
            this.showAuthButtons();
            return;
        }

        try {
            // Try to verify the token
            const response = await fetch('/api/admin/verify/', {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const userData = await response.json();
                if (userName) {
                    userName.textContent = userData.username || userData.name || 'Admin';
                }
                this.showUserMenu();
            } else {
                // Token is invalid, try to refresh
                await this.tryRefreshToken();
            }
        } catch (error) {
            console.error('Auth check failed:', error);
            this.showAuthButtons();
        }
    }

    async tryRefreshToken() {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
            this.showAuthButtons();
            return;
        }

        try {
            const response = await fetch('/api/token/refresh/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    refresh: refreshToken
                })
            });

            if (response.ok) {
                const data = await response.json();
                localStorage.setItem('access_token', data.access);
                this.checkAuthStatus(); // Re-check with new token
            } else {
                this.clearTokensAndShowAuth();
            }
        } catch (error) {
            console.error('Token refresh failed:', error);
            this.clearTokensAndShowAuth();
        }
    }

    showAuthButtons() {
        const authButtons = document.getElementById('authButtons');
        const userMenu = document.getElementById('userMenu');
        
        if (authButtons) authButtons.style.display = 'flex';
        if (userMenu) userMenu.style.display = 'none';
    }

    showUserMenu() {
        const authButtons = document.getElementById('authButtons');
        const userMenu = document.getElementById('userMenu');
        
        if (authButtons) authButtons.style.display = 'none';
        if (userMenu) userMenu.style.display = 'flex';
    }

    clearTokensAndShowAuth() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        this.showAuthButtons();
    }

    logout() {
        this.clearTokensAndShowAuth();
        // Redirect to login page
        window.location.href = '/login/';
    }

    setActiveNavLink() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.nav-link');
        
        navLinks.forEach(link => {
            link.classList.remove('active');
            
            const linkPath = link.getAttribute('href');
            const dataPage = link.dataset.page;
            
            // Exact path matching
            if (linkPath === currentPath) {
                link.classList.add('active');
                return;
            }
            
            // Special handling for specific pages
            if (currentPath.includes('admin-dashboard') && dataPage === 'admin-dashboard') {
                link.classList.add('active');
            } else if (currentPath.includes('admin-analytics') && dataPage === 'admin-analytics') {
                link.classList.add('active');
            } else if (currentPath.includes('feedback-management') && dataPage === 'feedback-management') {
                link.classList.add('active');
            } else if (currentPath.includes('admin-reprocess') && dataPage === 'admin-reprocess') {
                link.classList.add('active');
            }
        });
    }
}

// Initialize navbar when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new NavbarManager();
});

// Export for use in other scripts if needed
window.NavbarManager = NavbarManager;
