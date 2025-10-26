// Authentication utility functions
// This file provides reusable authentication functions across the application

/**
 * Refresh access token using refresh token
 * @returns {boolean} - True if refresh successful, false otherwise
 */
async function refreshAccessToken() {
    const refreshToken = localStorage.getItem('refresh_token');
    
    if (!refreshToken) {
        return false;
    }
    
    try {
        const response = await fetch('http://127.0.0.1:8000/api/token/refresh/', {
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
            return true;
        } else {
            // Refresh token is also invalid
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            return false;
        }
    } catch (error) {
        console.error('Token refresh failed:', error);
        return false;
    }
}

/**
 * Make an authenticated API request with automatic token refresh
 * @param {string} url - API endpoint URL
 * @param {object} options - Fetch options (method, headers, body, etc.)
 * @returns {Response} - Fetch response
 */
async function authenticatedFetch(url, options = {}) {
    const token = localStorage.getItem('access_token');
    
    if (!token) {
        throw new Error('No access token available');
    }
    
    // Add authorization header
    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    const requestOptions = {
        ...options,
        headers
    };
    
    try {
        const response = await fetch(url, requestOptions);
        
        // If unauthorized, try to refresh token and retry
        if (response.status === 401) {
            console.log('Token expired, attempting refresh...');
            const refreshSuccess = await refreshAccessToken();
            
            if (refreshSuccess) {
                // Retry with new token
                const newToken = localStorage.getItem('access_token');
                requestOptions.headers['Authorization'] = `Bearer ${newToken}`;
                return await fetch(url, requestOptions);
            } else {
                throw new Error('Authentication failed - please login again');
            }
        }
        
        return response;
    } catch (error) {
        console.error('Authenticated fetch error:', error);
        throw error;
    }
}

/**
 * Check if user is authenticated
 * @returns {boolean} - True if tokens exist, false otherwise
 */
function isAuthenticated() {
    const accessToken = localStorage.getItem('access_token');
    const refreshToken = localStorage.getItem('refresh_token');
    return !!(accessToken && refreshToken);
}

/**
 * Clear all authentication tokens
 */
function clearAuthTokens() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_info');
}

/**
 * Get current user info from token (basic decode)
 * @returns {object|null} - User info or null if no valid token
 */
function getCurrentUserInfo() {
    const token = localStorage.getItem('access_token');
    
    if (!token) {
        return null;
    }
    
    try {
        // Basic JWT decode (not secure validation, just for UI purposes)
        const payload = JSON.parse(atob(token.split('.')[1]));
        return {
            user_id: payload.user_id,
            email: payload.email,
            exp: payload.exp
        };
    } catch (error) {
        console.error('Token decode error:', error);
        return null;
    }
}

/**
 * Check if token is expired (client-side check only)
 * @returns {boolean} - True if token appears expired
 */
function isTokenExpired() {
    const userInfo = getCurrentUserInfo();
    
    if (!userInfo || !userInfo.exp) {
        return true;
    }
    
    const currentTime = Math.floor(Date.now() / 1000);
    return currentTime >= userInfo.exp;
}

/**
 * Logout user by clearing tokens and redirecting
 */
function logout() {
    clearAuthTokens();
    
    // Clear any other user-related data
    localStorage.removeItem('user_data');
    sessionStorage.clear();
    
    // Redirect to home page
    window.location.href = 'http://127.0.0.1:8000/website/';
}

/**
 * Initialize authentication UI elements
 * Call this on page load to show/hide auth-related elements
 */
function initAuthUI() {
    const isLoggedIn = isAuthenticated() && !isTokenExpired();
    const authButtons = document.getElementById('authButtons');
    const userMenu = document.getElementById('userMenu');
    const logoutBtn = document.getElementById('logoutBtn');
    const userName = document.getElementById('userName');
    
    console.log('initAuthUI called');
    console.log('isAuthenticated():', isAuthenticated());
    console.log('isTokenExpired():', isTokenExpired());
    console.log('isLoggedIn:', isLoggedIn);
    console.log('authButtons element:', authButtons);
    console.log('userMenu element:', userMenu);
    
    if (isLoggedIn) {
        console.log('User is logged in - showing logout, hiding auth buttons');
        // Hide register/login buttons and show logout
        if (authButtons) {
            authButtons.style.display = 'none';
            authButtons.hidden = true;
        }
        if (userMenu) {
            userMenu.hidden = false;
            userMenu.style.display = 'flex';
        }
        
        // Set up logout functionality
        if (logoutBtn) {
            logoutBtn.addEventListener('click', function(e) {
                e.preventDefault();
                logout();
            });
        }
        
        // Update user name with user info
        const userInfo = getCurrentUserInfo();
        if (userInfo && userInfo.email && userName) {
            userName.textContent = userInfo.email.split('@')[0];
        }
    } else {
        console.log('User is NOT logged in - showing auth buttons, hiding logout');
        // Show register/login buttons and hide user menu
        if (authButtons) {
            authButtons.style.display = 'flex';
            authButtons.hidden = false;
        }
        if (userMenu) {
            userMenu.hidden = true;
            userMenu.style.display = 'none';
        }
    }
}
