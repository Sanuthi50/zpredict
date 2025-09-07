// static/js/auth.js - Authentication functionality for Django
class AuthManager {
    constructor(apiBaseUrl) {
        this.API_BASE_URL = apiBaseUrl;
        this.TOKEN_KEY = 'access_token';
        this.REFRESH_KEY = 'refresh_token';
        this.CSRF_TOKEN = this.getCSRFToken();
    }

    // Get CSRF token from Django template
    getCSRFToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        return cookieValue || '';
    }

    // Check if user is already logged in
    async checkAuthStatus() {
        const token = this.getToken();
        if (token && !this.isTokenExpired()) {
            return { isAuthenticated: true, needsRefresh: false };
        } else {
            // Try refreshing token if refresh token exists
            const refreshToken = this.getRefreshToken();
            if (refreshToken) {
                const refreshSuccess = await this.refreshAccessToken(refreshToken);
                return { 
                    isAuthenticated: refreshSuccess, 
                    needsRefresh: !refreshSuccess 
                };
            } else {
                return { isAuthenticated: false, needsRefresh: false };
            }
        }
    }

    // Get stored access token
    getToken() {
        return localStorage.getItem(this.TOKEN_KEY);
    }

    // Get stored refresh token
    getRefreshToken() {
        return localStorage.getItem(this.REFRESH_KEY);
    }

    // Check if JWT is expired
    isTokenExpired() {
        const token = this.getToken();
        if (!token) return true;
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            return payload.exp * 1000 < Date.now();
        } catch {
            return true;
        }
    }

    // Refresh access token
    async refreshAccessToken(refreshToken) {
        try {
            const res = await fetch(`${this.API_BASE_URL}/token/refresh/`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.CSRF_TOKEN
                },
                body: JSON.stringify({ refresh: refreshToken })
            });

            if (res.ok) {
                const data = await res.json();
                localStorage.setItem(this.TOKEN_KEY, data.access);
                return true;
            } else {
                this.clearTokens();
                return false;
            }
        } catch (err) {
            console.error("Token refresh failed:", err);
            return false;
        }
    }

    // Login user
    async login(email, password) {
        try {
            const res = await fetch(`${this.API_BASE_URL}/admin/login/`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.CSRF_TOKEN
                },
                body: JSON.stringify({ email, password })
            });

            if (res.ok) {
                const data = await res.json();
                localStorage.setItem(this.TOKEN_KEY, data.access);
                localStorage.setItem(this.REFRESH_KEY, data.refresh);
                return { success: true, message: 'Login successful! Welcome back.' };
            } else {
                const error = await res.json();
                return { 
                    success: false, 
                    message: 'Login failed: ' + (error.detail || error.message || 'Invalid credentials') 
                };
            }
        } catch (err) {
            console.error('Login error:', err);
            return { 
                success: false, 
                message: 'Connection error. Please check your connection and try again.' 
            };
        }
    }

    // Logout user
    async logout() {
        try {
            // Optional: Call backend logout endpoint
            const token = this.getToken();
            if (token) {
                await fetch(`${this.API_BASE_URL}/admin/logout/`, {
                    method: 'POST',
                    headers: { 
                        'Authorization': `Bearer ${token}`,
                        'X-CSRFToken': this.CSRF_TOKEN
                    }
                });
            }
        } catch (err) {
            console.error('Logout API call failed:', err);
        } finally {
            this.clearTokens();
            return { success: true, message: 'Logged out successfully' };
        }
    }

    // Clear stored tokens
    clearTokens() {
        localStorage.removeItem(this.TOKEN_KEY);
        localStorage.removeItem(this.REFRESH_KEY);
    }

    // Get authorization header for API requests
    getAuthHeader() {
        const token = this.getToken();
        return token ? { 
            'Authorization': `Bearer ${token}`,
            'X-CSRFToken': this.CSRF_TOKEN
        } : { 'X-CSRFToken': this.CSRF_TOKEN };
    }

    // Check if current session is valid
    async validateSession() {
        const token = this.getToken();
        if (!token || this.isTokenExpired()) {
            return false;
        }
        return true;
    }

    // Get current user info
    getCurrentUserInfo() {
        const token = this.getToken();
        if (!token) return null;
        
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            return {
                userId: payload.user_id,
                email: payload.email,
                first_name: payload.first_name || 'Admin',
                last_name: payload.last_name || 'User',
                exp: payload.exp
            };
        } catch {
            return null;
        }
    }
}