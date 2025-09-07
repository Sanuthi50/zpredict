// static/js/upload-app.js - Upload dashboard controller
class UploadApp {
    constructor() {
        this.API_BASE_URL = 'http://127.0.0.1:8000/api';
        this.authManager = new AuthManager(this.API_BASE_URL);
        this.uploadManager = new UploadManager(this.API_BASE_URL, this.authManager);
        this.isInitialized = false;
        this.loginUrl = '/admin-login/'; // Admin login page URL
        this.currentPage = 1;
        this.itemsPerPage = 10;
        this.searchTerm = '';
    }

    // Initialize the upload application
    async init() {
        if (this.isInitialized) return;

        // Check authentication first
        const authValid = await this.checkAuthentication();
        if (!authValid) return;

        this.setupEventListeners();
        this.uploadManager.init();
        await this.loadInitialData();
        this.setupAutoRefresh();
        this.isInitialized = true;
        
        console.log('Upload App initialized successfully');
    }

    // Check if user is authenticated
    async checkAuthentication() {
        const authStatus = await this.authManager.checkAuthStatus();
        
        if (!authStatus.isAuthenticated) {
            this.redirectToLogin();
            return false;
        }

        this.displayUserInfo();
        return true;
    }

    // Display user information
    displayUserInfo() {
        const userInfo = this.authManager.getCurrentUserInfo();
        const welcomeMessage = document.getElementById('welcomeMessage');
        
        if (welcomeMessage && userInfo) {
            const displayName = userInfo.first_name || userInfo.email.split('@')[0];
            welcomeMessage.textContent = `Welcome, ${displayName}`;
        }
    }

    // Setup all event listeners
    setupEventListeners() {
        // Logout button
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.handleLogout());
        }

        // Reprocess button
        const reprocessBtn = document.getElementById('reprocessBtn');
        if (reprocessBtn) {
            reprocessBtn.addEventListener('click', () => this.handleReprocess());
        }

        // Refresh button
        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshUploads());
        }

        // Search functionality
        const searchInput = document.getElementById('searchUploads');
        if (searchInput) {
            let searchTimeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.searchTerm = e.target.value.trim();
                    this.currentPage = 1;
                    this.loadUploads();
                }, 300);
            });
        }

        // Pagination
        const prevPageBtn = document.getElementById('prevPage');
        const nextPageBtn = document.getElementById('nextPage');
        
        if (prevPageBtn) {
            prevPageBtn.addEventListener('click', () => this.previousPage());
        }
        
        if (nextPageBtn) {
            nextPageBtn.addEventListener('click', () => this.nextPage());
        }

        // Upload completion handler
        window.addEventListener('uploadCompleted', () => {
            this.refreshUploads();
            this.loadStats();
        });

        // Authentication required handler
        window.addEventListener('authRequired', () => {
            this.redirectToLogin();
        });

        // Window focus handler to refresh data
        window.addEventListener('focus', () => {
            if (this.isInitialized) {
                this.refreshUploads();
            }
        });
    }

    // Load initial data
    async loadInitialData() {
        await Promise.all([
            this.loadUploads(),
            this.loadStats()
        ]);
    }

    // Handle logout
    async handleLogout() {
        try {
            await this.authManager.logout();
            this.redirectToLogin();
        } catch (error) {
            console.error('Logout error:', error);
            // Force redirect even if logout fails
            this.redirectToLogin();
        }
    }

    // Handle reprocess
    async handleReprocess() {
        const reprocessBtn = document.getElementById('reprocessBtn');
        const originalHTML = reprocessBtn.innerHTML;
        
        try {
            reprocessBtn.disabled = true;
            reprocessBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
            
            await this.uploadManager.reprocessLatest();
            
            // Refresh data after reprocess
            setTimeout(() => {
                this.refreshUploads();
                this.loadStats();
            }, 2000);
            
        } catch (error) {
            console.error('Reprocess error:', error);
            this.uploadManager.showMessage('Error occurred during reprocessing', 'error');
        } finally {
            reprocessBtn.disabled = false;
            reprocessBtn.innerHTML = originalHTML;
        }
    }

    // Load uploads with pagination and search
    async loadUploads() {
        try {
            const isValid = await this.authManager.validateSession();
            if (!isValid) {
                this.redirectToLogin();
                return;
            }

            const authHeaders = this.authManager.getAuthHeader();
            const params = new URLSearchParams({
                page: this.currentPage,
                per_page: this.itemsPerPage,
                search: this.searchTerm
            });

            const res = await fetch(`${this.API_BASE_URL}/admin/upload/?${params}`, {
                headers: { 
                    ...authHeaders,
                    'Content-Type': 'application/json'
                }
            });

            if (!res.ok) {
                if (res.status === 401) {
                    this.redirectToLogin();
                }
                throw new Error('Failed to load uploads');
            }

            const data = await res.json();
            this.displayUploads(data.uploads || [], data.pagination || {});
            this.updatePagination(data.pagination || {});

        } catch (err) {
            console.error('Error loading uploads:', err);
            this.showUploadsError('Failed to load uploads');
        }
    }

    // Display uploads with enhanced UI
    displayUploads(uploads, pagination) {
        const uploadsContainer = document.getElementById('uploadsContainer');
        if (!uploadsContainer) return;

        uploadsContainer.innerHTML = '';

        if (uploads.length === 0) {
            uploadsContainer.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <h3>No uploads found</h3>
                    <p>${this.searchTerm ? 'No uploads match your search criteria.' : 'Start by uploading your first PDF document.'}</p>
                </div>
            `;
            return;
        }

        uploads.forEach((upload, index) => {
            const status = upload.processing_status || 'pending';
            const statusClass = {
                'pending': 'status-pending',
                'processing': 'status-processing',
                'completed': 'status-completed',
                'failed': 'status-failed'
            }[status.toLowerCase()] || 'status-pending';

            const uploadItem = document.createElement('div');
            uploadItem.classList.add('upload-item');
            uploadItem.innerHTML = `
                <div class="upload-info">
                    <div class="upload-header">
                        <strong class="filename">${upload.filename}</strong>
                        <span class="status-badge ${statusClass}">
                            ${this.getStatusIcon(status)} ${status.charAt(0).toUpperCase() + status.slice(1)}
                        </span>
                    </div>
                    <div class="upload-meta">
                        <small class="upload-date">
                            <i class="fas fa-calendar"></i>
                            Uploaded: ${new Date(upload.uploaded_at).toLocaleString()}
                        </small>
                        ${upload.file_size ? `<small class="file-size">
                            <i class="fas fa-file"></i>
                            ${this.formatFileSize(upload.file_size)}
                        </small>` : ''}
                        ${upload.description ? `<small class="description">
                            <i class="fas fa-info-circle"></i>
                            ${upload.description}
                        </small>` : ''}
                    </div>
                </div>
                <div class="upload-actions">
                    ${this.getUploadActions(upload, status)}
                </div>
            `;
            
            uploadsContainer.appendChild(uploadItem);
            
            // Add animation delay for each item
            setTimeout(() => {
                uploadItem.classList.add('animate-in');
            }, index * 100);
        });
    }

    // Get status icon
    getStatusIcon(status) {
        const icons = {
            'pending': '<i class="fas fa-clock"></i>',
            'processing': '<i class="fas fa-spinner fa-spin"></i>',
            'completed': '<i class="fas fa-check-circle"></i>',
            'failed': '<i class="fas fa-times-circle"></i>'
        };
        return icons[status.toLowerCase()] || '<i class="fas fa-question-circle"></i>';
    }

    // Get upload actions based on status
    getUploadActions(upload, status) {
        let actions = '';
        
        if (status === 'completed') {
            actions += `<button class="btn-small btn-outline" onclick="uploadApp.downloadFile('${upload.id}')">
                <i class="fas fa-download"></i> Download
            </button>`;
        }
        
        if (status === 'failed') {
            actions += `<button class="btn-small btn-secondary" onclick="uploadApp.retryUpload('${upload.id}')">
                <i class="fas fa-redo"></i> Retry
            </button>`;
        }
        
        actions += `<button class="btn-small btn-danger" onclick="uploadApp.deleteUpload('${upload.id}')">
            <i class="fas fa-trash"></i> Delete
        </button>`;
        
        return actions;
    }

    // Format file size
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Update pagination controls
    updatePagination(pagination) {
        const paginationDiv = document.getElementById('uploadsPagination');
        const prevBtn = document.getElementById('prevPage');
        const nextBtn = document.getElementById('nextPage');
        const pageInfo = document.getElementById('pageInfo');
        
        if (paginationDiv && pagination.total_pages > 1) {
            paginationDiv.style.display = 'flex';
            
            if (prevBtn) {
                prevBtn.disabled = pagination.current_page <= 1;
            }
            
            if (nextBtn) {
                nextBtn.disabled = pagination.current_page >= pagination.total_pages;
            }
            
            if (pageInfo) {
                pageInfo.textContent = `Page ${pagination.current_page} of ${pagination.total_pages}`;
            }
        } else if (paginationDiv) {
            paginationDiv.style.display = 'none';
        }
    }

    // Pagination methods
    previousPage() {
        if (this.currentPage > 1) {
            this.currentPage--;
            this.loadUploads();
        }
    }

    nextPage() {
        this.currentPage++;
        this.loadUploads();
    }

    // Load statistics
    async loadStats() {
        try {
            const isValid = await this.authManager.validateSession();
            if (!isValid) return;

            const authHeaders = this.authManager.getAuthHeader();
            const res = await fetch(`${this.API_BASE_URL}/admin/dashboard/`, {
                headers: { 
                    ...authHeaders,
                    'Content-Type': 'application/json'
                }
            });

            if (res.ok) {
                const data = await res.json();
                this.displayStats(data.stats || {});
            }
        } catch (err) {
            console.error('Error loading stats:', err);
        }
    }

    // Display statistics
    displayStats(stats) {
        const elements = {
            totalUploads: document.getElementById('totalUploads'),
            processingCount: document.getElementById('processingCount'),
            completedCount: document.getElementById('completedCount'),
            failedCount: document.getElementById('failedCount')
        };

        if (elements.totalUploads) elements.totalUploads.textContent = stats.total_uploads || '0';
        if (elements.processingCount) elements.processingCount.textContent = stats.pending_uploads || '0';
        if (elements.completedCount) elements.completedCount.textContent = stats.total_uploads || '0';
        if (elements.failedCount) elements.failedCount.textContent = '0';
    }

    // Refresh uploads
    async refreshUploads() {
        const refreshBtn = document.getElementById('refreshBtn');
        if (refreshBtn) {
            const originalHTML = refreshBtn.innerHTML;
            refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing...';
            refreshBtn.disabled = true;
            
            await this.loadUploads();
            
            setTimeout(() => {
                refreshBtn.innerHTML = originalHTML;
                refreshBtn.disabled = false;
            }, 500);
        } else {
            await this.loadUploads();
        }
    }

    // Setup auto-refresh
    setupAutoRefresh() {
        // Refresh every 30 seconds
        setInterval(() => {
            if (this.isInitialized && !document.hidden) {
                this.loadUploads();
                this.loadStats();
            }
        }, 30000);
    }

    // File actions
    async downloadFile(fileId) {
        try {
            const authHeaders = this.authManager.getAuthHeader();
            const res = await fetch(`${this.API_BASE_URL}/admin/download/${fileId}/`, {
                headers: authHeaders
            });
            
            if (res.ok) {
                const blob = await res.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `document_${fileId}.pdf`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            } else {
                throw new Error('Download failed');
            }
        } catch (err) {
            console.error('Download error:', err);
            this.uploadManager.showMessage('Download failed', 'error');
        }
    }

    async retryUpload(fileId) {
        try {
            const authHeaders = this.authManager.getAuthHeader();
            const res = await fetch(`${this.API_BASE_URL}/admin/retry/${fileId}/`, {
                method: 'POST',
                headers: authHeaders
            });
            
            if (res.ok) {
                this.uploadManager.showMessage('Retry initiated successfully', 'success');
                this.refreshUploads();
            } else {
                throw new Error('Retry failed');
            }
        } catch (err) {
            console.error('Retry error:', err);
            this.uploadManager.showMessage('Retry failed', 'error');
        }
    }

    async deleteUpload(fileId) {
        if (!confirm('Are you sure you want to delete this upload? This action cannot be undone.')) {
            return;
        }

        try {
            const authHeaders = this.authManager.getAuthHeader();
            const res = await fetch(`${this.API_BASE_URL}/admin/delete/${fileId}/`, {
                method: 'DELETE',
                headers: authHeaders
            });
            
            if (res.ok) {
                this.uploadManager.showMessage('Upload deleted successfully', 'success');
                this.refreshUploads();
                this.loadStats();
            } else {
                throw new Error('Delete failed');
            }
        } catch (err) {
            console.error('Delete error:', err);
            this.uploadManager.showMessage('Delete failed', 'error');
        }
    }

    // Show uploads error
    showUploadsError(message) {
        const uploadsContainer = document.getElementById('uploadsContainer');
        if (uploadsContainer) {
            uploadsContainer.innerHTML = `
                <div class="error-state">
                    <i class="fas fa-exclamation-triangle"></i>
                    <h3>Error Loading Uploads</h3>
                    <p>${message}</p>
                    <button class="btn btn-primary" onclick="uploadApp.refreshUploads()">
                        <i class="fas fa-retry"></i> Try Again
                    </button>
                </div>
            `;
        }
    }

    // Redirect to login
    redirectToLogin() {
        const currentPath = window.location.pathname;
        const nextParam = currentPath !== this.loginUrl ? `?next=${encodeURIComponent(currentPath)}` : '';
        window.location.href = this.loginUrl + nextParam;
    }
}

// Global app instance
let uploadApp;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', async () => {
    uploadApp = new UploadApp();
    await uploadApp.init();
});

// Export for external access
window.uploadApp = uploadApp;

// Add additional CSS for upload dashboard
const style = document.createElement('style');
style.textContent = `
    .upload-item {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding: 20px;
        border: 1px solid rgba(0, 0, 0, 0.1);
        border-radius: 10px;
        margin-bottom: 15px;
        background: white;
        transition: all 0.3s ease;
        opacity: 0;
        transform: translateY(20px);
    }

    .upload-item.animate-in {
        opacity: 1;
        transform: translateY(0);
    }

    .upload-item:hover {
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        transform: translateY(-2px);
    }

    .upload-info {
        flex: 1;
    }

    .upload-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }

    .filename {
        color: #2c3e50;
        font-size: 16px;
    }

    .upload-meta {
        display: flex;
        flex-direction: column;
        gap: 5px;
    }

    .upload-meta small {
        display: flex;
        align-items: center;
        gap: 8px;
        color: #7f8c8d;
        font-size: 13px;
    }

    .upload-actions {
        display: flex;
        gap: 10px;
        align-items: flex-start;
    }

    .btn-small {
        padding: 6px 12px;
        font-size: 12px;
        border-radius: 20px;
        border: none;
        cursor: pointer;
        transition: all 0.3s ease;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 5px;
    }

    .btn-outline {
        background: transparent;
        border: 1px solid #667eea !important;
        color: #667eea;
    }

    .btn-outline:hover {
        background: #667eea;
        color: white;
    }

    .btn-secondary {
        background: #6c757d;
        color: white;
    }

    .btn-secondary:hover {
        background: #5a6268;
    }

    .btn-danger {
        background: #dc3545;
        color: white;
    }

    .btn-danger:hover {
        background: #c82333;
    }

    .empty-state, .error-state {
        text-align: center;
        padding: 60px 20px;
        color: #7f8c8d;
    }

    .empty-state i, .error-state i {
        font-size: 48px;
        margin-bottom: 20px;
        opacity: 0.5;
    }

    .empty-state h3, .error-state h3 {
        margin-bottom: 10px;
        color: #2c3e50;
    }

    .uploads-controls {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 15px;
    }

    .search-box {
        position: relative;
        min-width: 250px;
    }

    .search-box input {
        width: 100%;
        padding: 10px 40px 10px 15px;
        border: 1px solid #ddd;
        border-radius: 25px;
        font-size: 14px;
    }

    .search-box i {
        position: absolute;
        right: 15px;
        top: 50%;
        transform: translateY(-50%);
        color: #7f8c8d;
    }

    .pagination {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 20px;
        margin-top: 30px;
        padding: 20px;
    }

    .pagination button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    @media (max-width: 768px) {
        .upload-item {
            flex-direction: column;
            gap: 15px;
        }

        .upload-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 10px;
        }

        .upload-actions {
            align-self: stretch;
            justify-content: center;
        }

        .uploads-controls {
            flex-direction: column;
            align-items: stretch;
        }

        .search-box {
            min-width: auto;
        }
    }
`;
document.head.appendChild(style);