// static/js/login-app.js - Login page controller
class LoginApp {
    constructor() {
        this.API_BASE_URL = 'http://127.0.0.1:8000/api';
        this.authManager = new AuthManager(this.API_BASE_URL);
        this.isInitialized = false;
        this.redirectUrl = '/admin-dashboard/'; // Change this to your upload page URL
    }

    // Initialize the login application
    async init() {
        if (this.isInitialized) return;

        // Check if user is already logged in
        await this.checkExistingAuth();
        this.setupEventListeners();
        this.setupFormValidation();
        this.isInitialized = true;
        
        console.log('Login App initialized successfully');
    }

    // Check if user is already authenticated
    async checkExistingAuth() {
        const authStatus = await this.authManager.checkAuthStatus();
        
        if (authStatus.isAuthenticated) {
            this.showMessage('You are already logged in. Redirecting...', 'success');
            setTimeout(() => {
                this.redirectToDashboard();
            }, 1500);
        }
    }

    // Setup event listeners
    setupEventListeners() {
        // Login form submit
        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        }

        // Forgot password link
        const forgotPasswordLink = document.querySelector('.forgot-password');
        if (forgotPasswordLink) {
            forgotPasswordLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.handleForgotPassword();
            });
        }

        // Register link
        const registerLink = document.querySelector('.register-link');
        if (registerLink) {
            registerLink.addEventListener('click', (e) => {
                e.preventDefault();
                this.handleRegisterRequest();
            });
        }

        // Enter key handling for better UX
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && document.activeElement.tagName !== 'BUTTON') {
                const loginForm = document.getElementById('loginForm');
                if (loginForm) {
                    loginForm.requestSubmit();
                }
            }
        });
    }

    // Setup form validation
    setupFormValidation() {
        const emailInput = document.getElementById('email');
        const passwordInput = document.getElementById('password');

        if (emailInput) {
            emailInput.addEventListener('blur', () => this.validateEmail(emailInput.value));
            emailInput.addEventListener('input', () => this.clearFieldError(emailInput));
        }

        if (passwordInput) {
            passwordInput.addEventListener('input', () => this.clearFieldError(passwordInput));
        }
    }

    // Handle login form submission
    async handleLogin(e) {
        e.preventDefault();
        this.clearMessages();

        const formData = new FormData(e.target);
        const email = formData.get('email')?.trim();
        const password = formData.get('password');
        const rememberMe = formData.get('remember_me') === 'on';

        // Client-side validation
        if (!this.validateForm(email, password)) {
            return;
        }

        // Show loading state
        const submitBtn = e.target.querySelector('button[type="submit"]');
        const originalHTML = submitBtn.innerHTML;
        this.setButtonLoading(submitBtn, true);

        try {
            const result = await this.authManager.login(email, password);
            
            if (result.success) {
                this.showMessage(result.message, 'success');
                
                // Handle "Remember me" functionality
                if (rememberMe) {
                    localStorage.setItem('remember_user', email);
                } else {
                    localStorage.removeItem('remember_user');
                }

                // Redirect after successful login
                setTimeout(() => {
                    this.redirectToDashboard();
                }, 1500);
            } else {
                this.showMessage(result.message, 'error');
                this.shakeForm();
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showMessage('An unexpected error occurred. Please try again.', 'error');
        } finally {
            this.setButtonLoading(submitBtn, false, originalHTML);
        }
    }

    // Form validation
    validateForm(email, password) {
        let isValid = true;

        if (!email) {
            this.showFieldError('email', 'Email is required');
            isValid = false;
        } else if (!this.validateEmail(email)) {
            isValid = false;
        }

        if (!password) {
            this.showFieldError('password', 'Password is required');
            isValid = false;
        } else if (password.length < 6) {
            this.showFieldError('password', 'Password must be at least 6 characters');
            isValid = false;
        }

        return isValid;
    }

    // Email validation
    validateEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        const isValid = emailRegex.test(email);
        
        if (!isValid && email) {
            this.showFieldError('email', 'Please enter a valid email address');
        }
        
        return isValid;
    }

    // Show field-specific error
    showFieldError(fieldName, message) {
        const field = document.getElementById(fieldName);
        if (field) {
            field.classList.add('error');
            
            // Remove existing error message
            const existingError = field.parentNode.querySelector('.field-error');
            if (existingError) {
                existingError.remove();
            }

            // Add new error message
            const errorDiv = document.createElement('div');
            errorDiv.className = 'field-error';
            errorDiv.textContent = message;
            field.parentNode.appendChild(errorDiv);
        }
    }

    // Clear field error
    clearFieldError(field) {
        field.classList.remove('error');
        const errorMsg = field.parentNode.querySelector('.field-error');
        if (errorMsg) {
            errorMsg.remove();
        }
    }

    // Handle forgot password
    handleForgotPassword() {
        const email = document.getElementById('email')?.value.trim();
        
        if (email && this.validateEmail(email)) {
            // You can implement forgot password functionality here
            this.showMessage(`Password reset instructions would be sent to ${email}`, 'info');
        } else {
            this.showMessage('Please enter a valid email address first', 'error');
            document.getElementById('email')?.focus();
        }
    }

    // Handle register request
    handleRegisterRequest() {
        this.showMessage('Please contact the administrator for account registration', 'info');
    }

    // Set button loading state
    setButtonLoading(button, isLoading, originalHTML = '') {
        if (isLoading) {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Signing In...';
        } else {
            button.disabled = false;
            button.innerHTML = originalHTML || '<i class="fas fa-sign-in-alt"></i> Sign In';
        }
    }

    // Shake form animation for errors
    shakeForm() {
        const loginCard = document.querySelector('.login-card');
        if (loginCard) {
            loginCard.style.animation = 'shake 0.5s ease-in-out';
            setTimeout(() => {
                loginCard.style.animation = '';
            }, 500);
        }
    }

    // Redirect to dashboard
    redirectToDashboard() {
        // Get the intended redirect URL from query params or use default
        const urlParams = new URLSearchParams(window.location.search);
        const next = urlParams.get('next') || this.redirectUrl;
        
        window.location.href = next;
    }

    // Show message
    showMessage(message, type) {
        const container = document.getElementById('loginMessage');
        if (container) {
            container.innerHTML = `<div class="message ${type}">${message}</div>`;
            
            // Auto-hide success and info messages
            if (type === 'success' || type === 'info') {
                setTimeout(() => {
                    container.innerHTML = '';
                }, 5000);
            }
        }
    }

    // Clear all messages
    clearMessages() {
        const loginMessage = document.getElementById('loginMessage');
        if (loginMessage) {
            loginMessage.innerHTML = '';
        }

        // Clear field errors
        document.querySelectorAll('.field-error').forEach(error => error.remove());
        document.querySelectorAll('.error').forEach(field => field.classList.remove('error'));
    }

    // Prefill remembered user
    prefillRememberedUser() {
        const rememberedEmail = localStorage.getItem('remember_user');
        if (rememberedEmail) {
            const emailInput = document.getElementById('email');
            const rememberCheckbox = document.querySelector('input[name="remember_me"]');
            
            if (emailInput) {
                emailInput.value = rememberedEmail;
            }
            
            if (rememberCheckbox) {
                rememberCheckbox.checked = true;
            }
        }
    }
}

// Global app instance
let loginApp;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', async () => {
    loginApp = new LoginApp();
    await loginApp.init();
    loginApp.prefillRememberedUser();
});

// Export for external access
window.loginApp = loginApp;

// Add CSS for animations and field errors
const style = document.createElement('style');
style.textContent = `
    @keyframes shake {
        0%, 20%, 40%, 60%, 80% { transform: translateX(0); }
        10%, 30%, 50%, 70%, 90% { transform: translateX(-10px); }
    }

    .field-error {
        color: #dc3545;
        font-size: 12px;
        margin-top: 5px;
        display: block;
    }

    .form-group input.error {
        border-color: #dc3545;
        box-shadow: 0 0 0 0.2rem rgba(220, 53, 69, 0.25);
    }

    .remember-forgot {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 15px 0;
    }

    .checkbox-label {
        display: flex;
        align-items: center;
        cursor: pointer;
        font-size: 14px;
    }

    .checkbox-label input {
        margin-right: 8px;
    }

    .forgot-password {
        color: #667eea;
        text-decoration: none;
        font-size: 14px;
    }

    .forgot-password:hover {
        text-decoration: underline;
    }

    .login-footer {
        text-align: center;
        margin-top: 20px;
        padding-top: 20px;
        border-top: 1px solid rgba(0, 0, 0, 0.1);
    }

    .login-footer p {
        margin: 0;
        color: #7f8c8d;
        font-size: 14px;
    }

    .register-link {
        color: #667eea;
        text-decoration: none;
    }

    .register-link:hover {
        text-decoration: underline;
    }

    .btn-login {
        width: 100%;
        padding: 12px;
        font-size: 16px;
        font-weight: 600;
        margin-top: 10px;
    }

    .stats-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 20px;
        margin-top: 20px;
    }

    .stat-item {
        text-align: center;
        padding: 15px;
        background: rgba(102, 126, 234, 0.1);
        border-radius: 10px;
    }

    .stat-number {
        font-size: 24px;
        font-weight: bold;
        color: #667eea;
    }

    .stat-label {
        font-size: 12px;
        color: #7f8c8d;
        margin-top: 5px;
    }
`;
document.head.appendChild(style);