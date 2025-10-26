// static/js/upload.js - File upload functionality for Django
class UploadManager {
    constructor(apiBaseUrl, authManager) {
        this.API_BASE_URL = apiBaseUrl;
        this.authManager = authManager;
        this.selectedFile = null;
        this.maxFileSize = 100 * 1024 * 1024; // 100MB
        this.allowedTypes = ['application/pdf'];
    }

    // Initialize upload functionality
    init() {
        this.setupEventListeners();
        this.resetFileInput();
    }

    // Setup all event listeners for upload functionality
    setupEventListeners() {
        const fileInput = document.getElementById('fileInput');
        const fileInputHidden = document.getElementById('fileInputHidden');
        const uploadForm = document.getElementById('uploadForm');

        if (!fileInput || !fileInputHidden || !uploadForm) {
            console.error('Upload elements not found in DOM');
            return;
        }

        // File input click handler
        fileInput.addEventListener('click', () => fileInputHidden.click());

        // Drag and drop handlers
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
            if (files.length > 0) this.handleFileSelection(files[0]);
        });

        // Hidden file input change handler
        fileInputHidden.addEventListener('change', (e) => {
            if (e.target.files.length > 0) this.handleFileSelection(e.target.files[0]);
        });

        // Upload form submit handler
        uploadForm.addEventListener('submit', (e) => this.handleUpload(e));
    }

    // Handle file selection validation
    handleFileSelection(file) {
        // Validate file type
        if (!this.allowedTypes.includes(file.type)) {
            this.showMessage('Please select a PDF file only.', 'error');
            return;
        }

        // Validate file size
        if (file.size > this.maxFileSize) {
            this.showMessage('File size must be less than 100MB.', 'error');
            return;
        }

        // File is valid, store it and update UI
        this.selectedFile = file;
        this.updateFileInputDisplay(file);
        this.clearMessages();
    }

    // Update file input display after file selection
    updateFileInputDisplay(file) {
        const fileInput = document.getElementById('fileInput');
        const fileTextP = fileInput.querySelector('.file-text p');
        
        fileInput.classList.add('has-file');
        if (fileTextP) {
            fileTextP.innerHTML = `<strong>${file.name}</strong><br><small>${(file.size / 1024 / 1024).toFixed(2)} MB</small>`;
        }

        // Update icon to show success
        const iconElement = fileInput.querySelector('.icon-file');
        if (iconElement) {
            iconElement.style.color = '#28a745';
        }
    }

    // Reset file input to initial state
    resetFileInput() {
        const fileInput = document.getElementById('fileInput');
        const fileInputHidden = document.getElementById('fileInputHidden');
        const fileTextP = fileInput?.querySelector('.file-text p');
        const iconElement = fileInput?.querySelector('.icon-file');
        
        if (fileInput) {
            fileInput.classList.remove('has-file');
        }
        
        if (fileTextP) {
            fileTextP.textContent = 'Click or drag PDF file here';
        }
        
        if (iconElement) {
            iconElement.style.color = '';
        }
        
        if (fileInputHidden) {
            fileInputHidden.value = '';
        }
        
        this.selectedFile = null;
    }

    // Handle file upload
    async handleUpload(e) {
        e.preventDefault();
        this.clearMessages();

        // Validate file selection
        if (!this.selectedFile) {
            this.showMessage('No PDF file selected.', 'error');
            return;
        }

        // Check authentication
        const isValid = await this.authManager.validateSession();
        if (!isValid) {
            this.showMessage('Authentication error. Please login again.', 'error');
            // Trigger re-authentication
            window.dispatchEvent(new CustomEvent('authRequired'));
            return;
        }

        const description = document.getElementById('description')?.value.trim() || '';
        const formData = new FormData();
        formData.append('pdf_file', this.selectedFile);
        formData.append('description', description);

        try {
            const result = await this.uploadFile(formData);
            if (result.success) {
                this.showMessage('File uploaded successfully!', 'success');
                this.resetFileInput();
                if (document.getElementById('description')) {
                    document.getElementById('description').value = '';
                }
                // Notify that upload completed successfully
                window.dispatchEvent(new CustomEvent('uploadCompleted'));
            } else {
                this.showMessage(result.message, 'error');
            }
        } catch (error) {
            this.showMessage('Unexpected error occurred.', 'error');
            console.error('Upload error:', error);
        }
    }

    // Upload file with progress tracking
    uploadFile(formData) {
        return new Promise((resolve) => {
            const progressBar = document.getElementById('progressBar');
            const progressFill = document.getElementById('progressFill');
            
            // Show progress bar
            if (progressBar && progressFill) {
                progressBar.style.display = 'block';
                progressFill.style.width = '0%';
            }

            const xhr = new XMLHttpRequest();
            xhr.open('POST', `${this.API_BASE_URL}/admin/upload/`, true);
            
            // Set authorization header
            const authHeaders = this.authManager.getAuthHeader();
            Object.keys(authHeaders).forEach(key => {
                xhr.setRequestHeader(key, authHeaders[key]);
            });

            // Track upload progress
            xhr.upload.onprogress = (event) => {
                if (event.lengthComputable && progressFill) {
                    const percentComplete = (event.loaded / event.total) * 100;
                    progressFill.style.width = percentComplete + '%';
                }
            };

            // Handle upload completion
            xhr.onload = () => {
                if (progressBar) {
                    progressBar.style.display = 'none';
                }
                
                if (xhr.status >= 200 && xhr.status < 300) {
                    resolve({ success: true, message: 'File uploaded successfully!' });
                } else {
                    let errorMsg = 'Upload failed.';
                    try {
                        const resp = JSON.parse(xhr.responseText);
                        errorMsg = resp.detail || resp.message || errorMsg;
                    } catch {}
                    resolve({ success: false, message: errorMsg });
                }
            };

            // Handle upload error
            xhr.onerror = () => {
                if (progressBar) {
                    progressBar.style.display = 'none';
                }
                resolve({ success: false, message: 'Upload failed due to network error.' });
            };

            xhr.send(formData);
        });
    }

    // Load and display recent uploads
    async loadUploads() {
        try {
            // Check authentication first
            const isValid = await this.authManager.validateSession();
            if (!isValid) return;

            const authHeaders = this.authManager.getAuthHeader();
            const res = await fetch(`${this.API_BASE_URL}/admin/upload/?per_page=5`, {
                headers: { 
                    ...authHeaders,
                    'Content-Type': 'application/json'
                }
            });

            if (!res.ok) {
                if (res.status === 401) {
                    // Unauthorized - trigger re-authentication
                    window.dispatchEvent(new CustomEvent('authRequired'));
                }
                throw new Error('Failed to load uploads');
            }

            const data = await res.json();
            this.displayUploads(data.uploads || []);

        } catch (err) {
            console.error('Error loading uploads:', err);
        }
    }

    // Display uploads in the UI
    displayUploads(uploads) {
        const uploadsContainer = document.getElementById('uploadsContainer');
        if (!uploadsContainer) return;

        uploadsContainer.innerHTML = '';

        if (uploads.length === 0) {
            uploadsContainer.innerHTML = '<p>No uploads found.</p>';
            return;
        }

        uploads.forEach(upload => {
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
                    ${upload.description ? `<br><small>Description: ${upload.description}</small>` : ''}
                </div>
                <span class="status-badge ${statusClass}">${status.charAt(0).toUpperCase() + status.slice(1)}</span>
            `;
            uploadsContainer.appendChild(uploadItem);
        });

        const uploadsList = document.getElementById('uploadsList');
        if (uploadsList) {
            uploadsList.style.display = 'block';
        }
    }

    // Show message in upload section
    showMessage(message, type) {
        const container = document.getElementById('uploadMessage');
        if (container) {
            container.innerHTML = `<div class="message ${type}">${message}</div>`;
            
            // Auto-hide success messages after 5 seconds
            if (type === 'success') {
                setTimeout(() => {
                    container.innerHTML = '';
                }, 5000);
            }
        }
    }

    // Clear upload messages
    clearMessages() {
        const uploadMessage = document.getElementById('uploadMessage');
        if (uploadMessage) {
            uploadMessage.innerHTML = '';
        }
    }

    // Handle reprocess button functionality
    async reprocessLatest() {
        try {
            const isValid = await this.authManager.validateSession();
            if (!isValid) {
                this.showMessage('Authentication error. Please login again.', 'error');
                window.dispatchEvent(new CustomEvent('authRequired'));
                return;
            }

            this.showMessage('Reprocessing latest PDF...', 'info');
            
            const authHeaders = this.authManager.getAuthHeader();
            const res = await fetch(`${this.API_BASE_URL}/admin/reprocess-pdf/`, {
                method: 'POST',
                headers: authHeaders
            });

            if (res.ok) {
                const result = await res.json();
                this.showMessage(result.message || 'Reprocessing started successfully!', 'success');
                // Reload uploads to show updated status
                setTimeout(() => this.loadUploads(), 2000);
            } else {
                const error = await res.json();
                this.showMessage(error.message || 'Failed to reprocess PDF', 'error');
            }
        } catch (err) {
            console.error('Reprocess error:', err);
            this.showMessage('Error occurred while reprocessing', 'error');
        }
    }
}