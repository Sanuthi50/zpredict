// DOM Elements
const chatHistoryList = document.getElementById('chatHistoryList');
const searchInput = document.getElementById('searchInput');
const filterButtons = document.querySelectorAll('.filter-btn');
const pagination = document.getElementById('pagination');
const toast = document.getElementById('toast');
const toastMessage = document.getElementById('toastMessage');

// Static assets (these will be injected from Django template)
let deleteIconUrl = window.DELETE_ICON_URL || "/static/images/delete.png";
let emptyIconUrl = window.EMPTY_ICON_URL || "/static/images/message.png";

// State
let currentPage = 1;
let totalPages = 1;
let currentFilter = 'all';
let currentSearch = '';
let chatHistory = [];

// API base URL - Fixed to match Django URL pattern
const API_BASE = "/api/chat-history";

// Authentication Functions
function getAuthToken() {
    return localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
}

function isAuthenticated() {
    const token = getAuthToken();
    if (!token) return false;
    
    try {
        // Check if token is expired (basic check)
        const payload = JSON.parse(atob(token.split('.')[1]));
        const now = Date.now() / 1000;
        return payload.exp > now;
    } catch (error) {
        return false;
    }
}

async function authenticatedFetch(url, options = {}) {
    const token = getAuthToken();
    
    const defaultHeaders = {
        'Content-Type': 'application/json',
    };
    
    if (token) {
        defaultHeaders['Authorization'] = `Bearer ${token}`;
    }
    
    const config = {
        ...options,
        headers: {
            ...defaultHeaders,
            ...options.headers,
        },
    };
    
    const response = await fetch(url, config);
    
    // Handle token refresh if needed
    if (response.status === 401 && token) {
        const refreshToken = localStorage.getItem('refresh_token') || sessionStorage.getItem('refresh_token');
        if (refreshToken) {
            try {
                const refreshResponse = await fetch('/api/token/refresh/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        refresh: refreshToken
                    }),
                });
                
                if (refreshResponse.ok) {
                    const data = await refreshResponse.json();
                    const storage = localStorage.getItem('access_token') ? localStorage : sessionStorage;
                    storage.setItem('access_token', data.access);
                    
                    // Retry original request with new token
                    config.headers['Authorization'] = `Bearer ${data.access}`;
                    return await fetch(url, config);
                }
            } catch (error) {
                console.error('Token refresh failed:', error);
            }
        }
    }
    
    return response;
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    if (!isAuthenticated()) {
        showToast('You need to log in to view chat history', 'error');
        setTimeout(() => {
            window.location.href = "/website/login/";
        }, 2000);
        return;
    }
    loadChatHistory();
    setupEventListeners();
});

// Event Listeners
function setupEventListeners() {
    // Search input
    searchInput.addEventListener('input', debounce(() => {
        currentSearch = searchInput.value.trim();
        currentPage = 1;
        loadChatHistory();
    }, 500));

    // Filter buttons
    filterButtons.forEach(button => {
        button.addEventListener('click', () => {
            filterButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            currentFilter = button.dataset.filter;
            currentPage = 1;
            loadChatHistory();
        });
    });
}

// Load Chat History
async function loadChatHistory() {
    showLoading();

    try {
        let url = `${API_BASE}/?page=${currentPage}`;

        if (currentSearch) {
            url += `&search=${encodeURIComponent(currentSearch)}`;
        }
        
        // Updated filter handling to match Django ViewSet
        if (currentFilter === 'recent') {
            url += '&ordering=-asked_at';
        } else if (currentFilter === 'oldest') {
            url += '&ordering=asked_at';
        }

        const response = await authenticatedFetch(url);

        if (response.status === 401) {
            showToast('Session expired. Please log in again.', 'error');
            // Clear tokens
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            sessionStorage.removeItem('access_token');
            sessionStorage.removeItem('refresh_token');
            setTimeout(() => window.location.href = "/website/login/", 2000);
            return;
        }

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}: Failed to load chat history`);
        }

        const data = await response.json();
        chatHistory = data.results || data;

        renderChatHistory();
        if (data.count !== undefined) {
            totalPages = Math.ceil(data.count / 10); // Assuming 10 items per page
            renderPagination();
        } else if (Array.isArray(data) && data.length === 0) {
            totalPages = 1;
            renderPagination();
        }

    } catch (error) {
        console.error('Error loading chat history:', error);
        showToast(error.message, 'error');
        renderEmptyState();
    }
}

// Render Chat History
function renderChatHistory() {
    if (!chatHistory || chatHistory.length === 0) {
        renderEmptyState();
        return;
    }

    chatHistoryList.innerHTML = '';

    chatHistory.forEach(chat => {
        const chatItem = document.createElement('div');
        chatItem.className = 'chat-item';

        // Format date properly
        const askedAt = new Date(chat.asked_at).toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });

        chatItem.innerHTML = `
            <div class="chat-header">
                <div class="chat-date">${askedAt}</div>
                <div class="chat-actions">
                    <button class="action-btn delete-btn" data-id="${chat.id}" title="Delete">
                        <img src="${deleteIconUrl}" alt="Delete" class="action-icon">
                    </button>
                </div>
            </div>
            <div class="chat-content">
                <div class="chat-question">
                    <strong>Q:</strong> ${escapeHtml(chat.question)}
                </div>
                <div class="chat-answer">
                    <strong>A:</strong> ${escapeHtml(chat.answer)}
                </div>
            </div>
        `;

        chatHistoryList.appendChild(chatItem);
    });

    // Add delete event listeners
    document.querySelectorAll('.delete-btn').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            const chatId = button.dataset.id;
            deleteChatHistory(chatId);
        });
    });
}

// Render Empty State
function renderEmptyState() {
    chatHistoryList.innerHTML = `
        <div class="empty-state">
            <div class="empty-icon">
                <img src="${emptyIconUrl}" alt="No History" class="empty-image">
            </div>
            <p class="empty-text">
                ${currentSearch ? `No chat history found for "${currentSearch}"` : 'No chat history found'}
            </p>
            <a href="/website/chat/" class="primary-btn">Start Chatting</a>
        </div>
    `;
    pagination.innerHTML = '';
}

// Render Pagination
function renderPagination() {
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }

    let paginationHTML = '';

    // Previous button
    paginationHTML += `
        <button class="page-btn" ${currentPage === 1 ? 'disabled' : ''} data-page="${currentPage - 1}">
            ← Previous
        </button>
    `;

    // Page numbers with improved logic
    const maxVisiblePages = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
    
    // Adjust start page if we're near the end
    if (endPage - startPage + 1 < maxVisiblePages) {
        startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }

    // First page and ellipsis
    if (startPage > 1) {
        paginationHTML += `
            <button class="page-btn" data-page="1">1</button>
        `;
        if (startPage > 2) {
            paginationHTML += `<span class="page-dots">...</span>`;
        }
    }

    // Page numbers
    for (let i = startPage; i <= endPage; i++) {
        paginationHTML += `
            <button class="page-btn ${i === currentPage ? 'active' : ''}" data-page="${i}">
                ${i}
            </button>
        `;
    }

    // Last page and ellipsis
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            paginationHTML += `<span class="page-dots">...</span>`;
        }
        paginationHTML += `
            <button class="page-btn" data-page="${totalPages}">${totalPages}</button>
        `;
    }

    // Next button
    paginationHTML += `
        <button class="page-btn" ${currentPage === totalPages ? 'disabled' : ''} data-page="${currentPage + 1}">
            Next →
        </button>
    `;

    pagination.innerHTML = paginationHTML;

    // Add event listeners to pagination buttons
    pagination.querySelectorAll('.page-btn').forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            if (!button.disabled && !button.classList.contains('active')) {
                currentPage = parseInt(button.dataset.page);
                loadChatHistory();
            }
        });
    });
}

// Delete Chat History (Soft Delete)
async function deleteChatHistory(chatId) {
    if (!confirm('Are you sure you want to delete this chat?')) {
        return;
    }

    try {
        const response = await authenticatedFetch(`${API_BASE}/${chatId}/`, {
            method: 'DELETE'
        });

        if (response.status === 204 || response.status === 200) {
            showToast('Chat deleted successfully', 'success');
            
            // Animate removal
            const chatItem = document.querySelector(`.delete-btn[data-id="${chatId}"]`).closest('.chat-item');
            if (chatItem) {
                chatItem.style.transition = 'all 0.3s ease';
                chatItem.style.opacity = '0';
                chatItem.style.transform = 'translateX(100px)';
                
                setTimeout(() => {
                    chatItem.remove();
                    // Reload if no items left on current page
                    if (document.querySelectorAll('.chat-item').length === 0) {
                        // If we're not on page 1 and this was the last item, go to previous page
                        if (currentPage > 1 && chatHistory.length === 1) {
                            currentPage--;
                        }
                        loadChatHistory();
                    }
                }, 300);
            }
        } else {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Failed to delete chat');
        }
    } catch (error) {
        console.error('Error deleting chat:', error);
        showToast(error.message, 'error');
    }
}

// Show Loading State
function showLoading() {
    chatHistoryList.innerHTML = `
        <div class="loading">
            <div class="loading-spinner"></div>
            <p>Loading chat history...</p>
        </div>
    `;
    pagination.innerHTML = '';
}

// Show Toast Notification
function showToast(message, type = '') {
    if (toast && toastMessage) {
        toastMessage.textContent = message;
        toast.className = `toast ${type}`;
        toast.classList.add('show');

        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    } else {
        // Fallback to console if toast elements don't exist
        console.log(`${type.toUpperCase()}: ${message}`);
    }
}

// Utility Functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe
        .toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Export functions for potential use elsewhere
window.ChatHistory = {
    loadChatHistory,
    deleteChatHistory,
    showToast
};