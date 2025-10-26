const API_BASE_URL = 'http://127.0.0.1:8000/api';
    const TOKEN_KEY = 'access_token';
    const REFRESH_KEY = 'refresh_token';

    let selectedFile = null;

    // Check if user is already logged in (via stored token)
    function checkAuthStatus() {
        const token = localStorage.getItem(TOKEN_KEY);
        if (token && !isTokenExpired()) {
            showUploadSection();
            loadUploads();
        } else {
            // Try refreshing token if refresh token exists
            const refreshToken = localStorage.getItem(REFRESH_KEY);
            if (refreshToken) {
                refreshAccessToken(refreshToken).then(valid => {
                    if (valid) {
                        showUploadSection();
                        loadUploads();
                    } else {
                        showLoginSection();
                    }
                });
            } else {
                showLoginSection();
            }
        }
    }

    // Helper: Check if JWT is expired
    function isTokenExpired() {
        const token = localStorage.getItem(TOKEN_KEY);
        if (!token) return true;
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            return payload.exp * 1000 < Date.now(); // Expired?
        } catch {
            return true;
        }
    }

    // Refresh access token
    async function refreshAccessToken(refreshToken) {
        try {
            const res = await fetch(`${API_BASE_URL}/token/refresh/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh: refreshToken })
            });

            if (res.ok) {
                const data = await res.json();
                localStorage.setItem(TOKEN_KEY, data.access);
                return true;
            } else {
                localStorage.removeItem(TOKEN_KEY);
                localStorage.removeItem(REFRESH_KEY);
                return false;
            }
        } catch (err) {
            console.error("Token refresh failed:", err);
            return false;
        }
    }

    // Login Form Handler
    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        clearMessages();
        const formData = new FormData(e.target);
        const loginData = {
            email: formData.get('email'),
            password: formData.get('password')
        };

        try {
            // Use your custom admin login endpoint with /api prefix
            const res = await fetch(`${API_BASE_URL}/admin/login/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(loginData)
            });

            if (res.ok) {
                const data = await res.json();
                localStorage.setItem(TOKEN_KEY, data.access);
                localStorage.setItem(REFRESH_KEY, data.refresh);
                showMessage('Login successful!', 'success', 'loginMessage');
                setTimeout(() => {
                    showUploadSection();
                    loadUploads();
                }, 1000);
            } else {
                const error = await res.json();
                showMessage('Login failed: ' + (error.detail || error.message || 'Invalid credentials'), 'error', 'loginMessage');
            }
        } catch (err) {
            showMessage('Connection error. Is the server running?', 'error', 'loginMessage');
            console.error(err);
        }
    });

    // Logout Handler
    document.getElementById('logoutBtn').addEventListener('click', () => {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(REFRESH_KEY);
        showLoginSection();
        clearMessages();
    });

    // File Input Handlers
    const fileInput = document.getElementById('fileInput');
    const fileInputHidden = document.getElementById('fileInputHidden');

    fileInput.addEventListener('click', () => fileInputHidden.click());

    fileInput.addEventListener('dragover', (e) => {
        e.preventDefault();
        fileInput.classList.add('dragover');
    });

    fileInput.addEventListener('dragleave', () => {
        fileInput.classList.remove('dragover');
    });

    fileInput.addEventListener('drop', (e) => {
        e.preventDefault();
        fileInput.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) handleFileSelection(files[0]);
    });

    fileInputHidden.addEventListener('change', (e) => {
        if (e.target.files.length > 0) handleFileSelection(e.target.files[0]);
    });

    function handleFileSelection(file) {
        if (file.type !== 'application/pdf') {
            showMessage('Please select a PDF file only.', 'error', 'uploadMessage');
            return;
        }
        if (file.size > 100 * 1024 * 1024) {
            showMessage('File size must be less than 100MB.', 'error', 'uploadMessage');
            return;
        }

        selectedFile = file;
        fileInput.classList.add('has-file');
        fileInput.innerHTML = `
            <div class="file-text">
                <div class="file-icon">✅</div>
                <p><strong>${file.name}</strong></p>
                <small>${(file.size / 1024 / 1024).toFixed(2)} MB</small>
            </div>
        `;
    }

    // Upload Form Handler
    document.getElementById('uploadForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        clearMessages();

        if (!selectedFile) {
            showMessage('No PDF file selected.', 'error', 'uploadMessage');
            return;
        }

        const description = document.getElementById('description').value.trim();

        const formData = new FormData();
        formData.append('pdf_file', selectedFile); // key matches backend expected field
        formData.append('description', description);

        // Show progress bar
        const progressBar = document.getElementById('progressBar');
        const progressFill = document.getElementById('progressFill');
        progressBar.style.display = 'block';
        progressFill.style.width = '0%';

        try {
            const token = localStorage.getItem(TOKEN_KEY);
            if (!token) {
                showMessage('Authentication error. Please login again.', 'error', 'uploadMessage');
                showLoginSection();
                return;
            }

            const xhr = new XMLHttpRequest();
            xhr.open('POST', `${API_BASE_URL}/admin/upload/`, true);
            xhr.setRequestHeader('Authorization', `Bearer ${token}`);

            xhr.upload.onprogress = (event) => {
                if (event.lengthComputable) {
                    const percentComplete = (event.loaded / event.total) * 100;
                    progressFill.style.width = percentComplete + '%';
                }
            };

            xhr.onload = () => {
                progressBar.style.display = 'none';
                if (xhr.status >= 200 && xhr.status < 300) {
                    showMessage('File uploaded successfully!', 'success', 'uploadMessage');
                    selectedFile = null;
                    resetFileInput();
                    document.getElementById('description').value = '';
                    loadUploads();
                } else {
                    let errorMsg = 'Upload failed.';
                    try {
                        const resp = JSON.parse(xhr.responseText);
                        errorMsg = resp.detail || resp.message || errorMsg;
                    } catch {}
                    showMessage(errorMsg, 'error', 'uploadMessage');
                }
            };

            xhr.onerror = () => {
                progressBar.style.display = 'none';
                showMessage('Upload failed due to network error.', 'error', 'uploadMessage');
            };

            xhr.send(formData);
        } catch (err) {
            progressBar.style.display = 'none';
            showMessage('Unexpected error occurred.', 'error', 'uploadMessage');
            console.error(err);
        }
    });

    function resetFileInput() {
        fileInput.classList.remove('has-file');
        fileInput.innerHTML = `
            <div class="file-text">
                <div class="file-icon">📄</div>
                <p>Click or drag PDF file here</p>
                <small>Maximum size: 100MB</small>
            </div>
        `;
        fileInputHidden.value = '';
    }

    // Load recent uploads and show in uploads list
    async function loadUploads() {
        try {
            const token = localStorage.getItem(TOKEN_KEY);
            if (!token) return;

            const res = await fetch(`${API_BASE_URL}/admin/dashboard/`, {
                headers: { 
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!res.ok) {
                if (res.status === 401) {
                    // Unauthorized - token expired or invalid
                    showLoginSection();
                }
                throw new Error('Failed to load uploads');
            }

            const data = await res.json();
            const uploadsContainer = document.getElementById('uploadsContainer');
            uploadsContainer.innerHTML = '';

            // Important: Backend returns { recent_uploads: [...] }, not a bare array
            const uploads = data.recent_uploads || [];

            if (uploads.length === 0) {
                uploadsContainer.innerHTML = '<p>No uploads found.</p>';
                return;
            }

            uploads.forEach(upload => {
                // Use the backend field 'processing_status' not 'status'
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
                    <div>
                        <strong>${upload.filename}</strong><br />
                        <small>Uploaded: ${new Date(upload.uploaded_at).toLocaleString()}</small>
                    </div>
                    <span class="status-badge ${statusClass}">${status.charAt(0).toUpperCase() + status.slice(1)}</span>
                `;
                uploadsContainer.appendChild(uploadItem);
            });

            document.getElementById('uploadsList').style.display = 'block';

        } catch (err) {
            console.error('Error loading uploads:', err);
        }
    }

    // Utility: Show message in given elementId
    function showMessage(message, type, elementId) {
        const container = document.getElementById(elementId);
        container.innerHTML = `<div class="message ${type}">${message}</div>`;
    }

    function clearMessages() {
        ['loginMessage', 'uploadMessage'].forEach(id => {
            document.getElementById(id).innerHTML = '';
        });
    }

    function showLoginSection() {
        document.getElementById('loginSection').style.display = 'block';
        document.getElementById('uploadSection').style.display = 'none';
        document.getElementById('uploadsList').style.display = 'none';
        document.getElementById('logoutBtn').style.display = 'none';
    }

    function showUploadSection() {
        document.getElementById('loginSection').style.display = 'none';
        document.getElementById('uploadSection').style.display = 'block';
        document.getElementById('uploadsList').style.display = 'block';
        document.getElementById('logoutBtn').style.display = 'block';
    }

    // On page load, check if already logged in
    window.addEventListener('load', () => {
        checkAuthStatus();
        resetFileInput();
    });