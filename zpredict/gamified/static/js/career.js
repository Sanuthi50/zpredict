/**
 * @fileoverview Main script for the Career Recommendation System frontend.
 * This file handles all client-side logic for career predictions,
 * saving, viewing, and deleting recommendations within a single-page
 * application using Bootstrap tabs.
 */

// =====================================
// UI Utilities Module
// =====================================
// This module handles generic UI interactions like toasts and loading states.
const UiUtils = (function() {
    /**
     * Shows a toast notification at the bottom of the page.
     * @param {string} message - The message to display.
     * @param {string} type - 'success' or 'danger' for styling.
     */
    function showToast(message, type) {
        const toastContainer = document.querySelector('.toast-container');
        const toast = document.createElement('div');
        toast.classList.add('toast', 'align-items-center', 'text-white', 'border-0', 'show');
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');

        if (type === 'success') {
            toast.classList.add('bg-success');
        } else if (type === 'danger') {
            toast.classList.add('bg-danger');
        }

        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        toastContainer.appendChild(toast);

        // Automatically hide after 5 seconds
        setTimeout(() => toast.remove(), 5000);
    }

    /**
     * Toggles the loading state of a button.
     * @param {string} btnId - The ID of the button element.
     * @param {boolean} isLoading - True to show loading, false to hide.
     */
    function toggleLoadingButton(btnId, isLoading) {
        const button = document.getElementById(btnId);
        const textSpan = button.querySelector(`#${btnId}-text`);
        const loadingSpan = button.querySelector(`#${btnId}-loading`);
        if (isLoading) {
            textSpan.classList.add('d-none');
            loadingSpan.classList.remove('d-none');
            button.disabled = true;
        } else {
            textSpan.classList.remove('d-none');
            loadingSpan.classList.add('d-none');
            button.disabled = false;
        }
    }

    return {
        showToast,
        toggleLoadingButton
    };
})();


// =====================================
// API Service Module
// =====================================
// This module handles all API requests with authentication.
const ApiService = (function() {
    /**
     * Retrieves the JWT access token from local storage.
     * Uses auth-utils.js functions if available, fallback to direct access.
     * @returns {string|null} The JWT token or null if not found.
     */
    function getToken() {
        // Try auth-utils function first if available
        if (typeof getCurrentUserInfo === 'function') {
            const userInfo = getCurrentUserInfo();
            if (userInfo && !isTokenExpired()) {
                return localStorage.getItem('access_token');
            }
        }
        return localStorage.getItem('access_token');
    }

    /**
     * A generic function to make authenticated API requests.
     * @param {string} url - The API endpoint URL.
     * @param {string} method - The HTTP method (e.g., 'GET', 'POST', 'DELETE').
     * @param {object} [body=null] - The request body data for POST/PUT.
     * @returns {Promise<object>} The JSON response data from the API.
     * @throws {Error} Throws an error if the network response is not OK.
     */
    async function fetchApi(url, method, body = null) {
        const token = getToken();
        if (!token) {
            UiUtils.showToast('Please log in to access this feature.', 'danger');
            throw new Error('User is not authenticated.');
        }

        console.log(`Making ${method} request to ${url}`, { body });

        try {
            // Use authenticatedFetch if available (from auth-utils.js)
            let response;
            if (typeof authenticatedFetch === 'function') {
                response = await authenticatedFetch(url, {
                    method: method,
                    body: body ? JSON.stringify(body) : null
                });
            } else {
                // Fallback to manual fetch
                const headers = {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                };

                const options = {
                    method: method,
                    headers: headers,
                    body: body ? JSON.stringify(body) : null
                };

                response = await fetch(url, options);
            }

            console.log(`Response status: ${response.status}`);

            if (!response.ok) {
                let errorData;
                try {
                    errorData = await response.json();
                } catch (e) {
                    errorData = { error: await response.text() };
                }
                console.error('API Error:', errorData);
                const errorMessage = errorData.detail || errorData.error || `HTTP error! Status: ${response.status}`;
                UiUtils.showToast(errorMessage, 'danger');
                throw new Error(errorMessage);
            }

            // Handle successful DELETE requests with no content
            if (response.status === 204) {
                return {};
            }

            return response.json();
        } catch (error) {
            console.error('fetchApi error:', error);
            throw error;
        }
    }

    return {
        fetchApi
    };
})();

// =====================================
// Career Actions & UI Renderer Module
// =====================================
// This module combines business logic and UI rendering for careers.
const CareerModule = (function() {

    // --- Private Helper Functions ---

    /**
     * Helper function to generate HTML for skills or abilities.
     * @param {string} title - The title for the section (e.g., 'Skills').
     * @param {Array<object>} items - The array of skill or ability objects.
     * @returns {string} The HTML string for the list or an empty string.
     */
    function renderSkillsOrAbilities(title, items) {
        if (!items || !Array.isArray(items) || items.length === 0) {
            return '';
        }
        const listItems = items.map(item => `
            <li>${item['Element Name'] || item['Element_Name'] || item.name}: <strong>${item['Data Value'] ? item['Data Value'].toFixed(2) : (item['Data_Value'] ? item['Data_Value'].toFixed(2) : 'N/A')}</strong></li>
        `).join('');
        return `
            <div class="mt-3">
                <h6 class="mb-1">${title}:</h6>
                <ul>${listItems}</ul>
            </div>
        `;
    }

    /**
     * Renders a single recommendation card.
     * @param {object} rec - The recommendation data.
     * @param {string} sessionId - The current session ID.
     * @returns {string} The HTML string for the card.
     */
    function renderRecommendationCard(rec, sessionId) {
        return `
            <div class="col-lg-6 mb-4">
                <div class="career-card">
                    <h5 class="career-title">${rec.title || 'Career Title'}</h5>
                    <div class="career-details">
                        <p><strong><i class="fas fa-briefcase"></i> Linked Occupation:</strong> ${rec.occupation || 'N/A'}</p>
                        <p><strong><i class="fas fa-chart-line"></i> Vacancies:</strong> ${rec.vacancies || 'N/A'}</p>
                        <p><strong><i class="fas fa-star-half-alt"></i> Combined Score:</strong> ${rec.combined_score ? rec.combined_score.toFixed(4) : 'N/A'}</p>
                        <p><strong><i class="fas fa-percent"></i> Similarity:</strong> ${rec.similarity_score ? (rec.similarity_score * 100).toFixed(2) + '%' : 'N/A'}</p>
                    </div>
                    ${renderSkillsOrAbilities('Skills', rec.skills)}
                    ${renderSkillsOrAbilities('Abilities', rec.abilities)}
                    <button class="btn btn-primary mt-3 save-button" 
                        data-career-code="${rec.career_code}" 
                        data-career-title="${rec.title}" 
                        data-session-id="${sessionId}" 
                        data-match-score="${rec.combined_score}">
                        <i class="fas fa-bookmark me-2"></i>Save Career
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Renders a single saved prediction card.
     * @param {object} pred - The saved prediction data.
     * @returns {string} The HTML string for the card.
     */
    function renderSavedPredictionCard(pred) {
        return `
            <div class="col-lg-6 mb-4" data-prediction-id="${pred.id}">
                <div class="career-card">
                    <h5 class="career-title">${pred.career_title}</h5>
                    <div class="career-details">
                        <p><strong><i class="fas fa-code"></i> Code:</strong> ${pred.career_code}</p>
                        <p><strong><i class="fas fa-star"></i> Match Score:</strong> ${pred.match_score ? pred.match_score.toFixed(4) : 'N/A'}</p>
                        <p><strong><i class="fas fa-calendar-check"></i> Saved On:</strong> ${new Date(pred.saved_at).toLocaleDateString()}</p>
                        <p><strong><i class="fas fa-sticky-note"></i> Notes:</strong> ${pred.notes || 'No notes'}</p>
                    </div>
                    <button class="btn btn-danger mt-3 delete-button" data-prediction-id="${pred.id}">
                        <i class="fas fa-trash-alt me-2"></i>Delete
                    </button>
                </div>
            </div>
        `;
    }

    // --- Public Functions ---

    /**
     * Handles the career prediction process.
     * This function initiates a new career session on the backend and renders the results.
     * @param {Event} event - The form submission event.
     */
    async function getRecommendations(event) {
        event.preventDefault();

        const degreeProgram = document.getElementById('degree-program').value.trim();
        if (!degreeProgram) {
            UiUtils.showToast('Please enter a degree program.', 'danger');
            return;
        }

        UiUtils.toggleLoadingButton('predict-btn', true);
        document.getElementById('results-section').classList.add('d-none');

        try {
            const data = await ApiService.fetchApi('/api/recommendations/', 'POST', {
                degree_program: degreeProgram,
                save_session: true
            });

            // Update UI with results
            const container = document.getElementById('recommendations-container');
            container.innerHTML = '';
            data.recommendations.forEach(rec => {
                container.innerHTML += renderRecommendationCard(rec, data.session_id);
            });

            // Update result count and show section
            document.getElementById('results-count').textContent = `${data.total_predictions} results`;
            document.getElementById('results-section').classList.remove('d-none');
            document.getElementById('session-badge').classList.remove('d-none');

            // Attach event listeners to the new "Save" buttons
            document.querySelectorAll('.save-button').forEach(button => {
                button.addEventListener('click', saveCareerPrediction);
            });

        } catch (error) {
            // Error handling is done inside ApiService.fetchApi
        } finally {
            UiUtils.toggleLoadingButton('predict-btn', false);
        }
    }

    /**
     * Saves a single career prediction.
     * @param {Event} event - The click event from the save button.
     */
    async function saveCareerPrediction(event) {
        const button = event.target;
        const { careerCode, careerTitle, sessionId, matchScore } = button.dataset;

        console.log('Save button data:', { careerCode, careerTitle, sessionId, matchScore });

        button.disabled = true;
        button.innerHTML = '<span class="loading me-2"></span>Saving...';

        const payload = {
            career_code: careerCode,
            career_title: careerTitle,
            match_score: parseFloat(matchScore),
            session_id: parseInt(sessionId),
            recommended_level: 'Recommended',
            notes: 'Saved from career prediction system'
        };
        
        console.log('Sending payload:', payload);

        try {
            const result = await ApiService.fetchApi('/api/career-predictions/', 'POST', payload);
            console.log('Save result:', result);

            button.innerHTML = '<i class="fas fa-check me-2"></i>Saved!';
            button.classList.remove('btn-primary');
            button.classList.add('btn-success');
            UiUtils.showToast('Career saved successfully!', 'success');
        } catch (error) {
            console.error('Save career error:', error);
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-bookmark me-2"></i>Save Career';
            // Error handling is done inside ApiService.fetchApi
        }
    }

    /**
     * Fetches and displays a user's saved career predictions.
     */
    async function fetchAndDisplaySavedCareers() {
        const listContainer = document.getElementById('saved-container');
        if (!listContainer) return;

        const noSavedMessage = document.getElementById('no-saved-message');
        
        // Show loading state
        listContainer.innerHTML = '<p class="text-center text-muted">Loading saved careers...</p>';
        if (noSavedMessage) {
            noSavedMessage.classList.add('d-none');
        }

        try {
            const savedPredictions = await ApiService.fetchApi('/api/career-predictions/', 'GET');
            
            // Clear the loading message
            listContainer.innerHTML = '';
            
            if (!savedPredictions || savedPredictions.length === 0) {
                listContainer.innerHTML = `
                    <p class="text-center text-muted" id="no-saved-message">
                        You haven't saved any recommendations yet.
                    </p>`;
            } else {
                savedPredictions.forEach(pred => {
                    listContainer.innerHTML += renderSavedPredictionCard(pred);
                });
                // Attach event listeners to the new "Delete" buttons
                document.querySelectorAll('.delete-button').forEach(button => {
                    button.addEventListener('click', deleteSavedPrediction);
                });
            }
        } catch (error) {
            listContainer.innerHTML = ''; // Clear loading message
            // Error handling is done inside ApiService.fetchApi
        }
    }

    /**
     * Soft-deletes a saved career prediction.
     * @param {Event} event - The click event from the delete button.
     */
    async function deleteSavedPrediction(event) {
        const button = event.target;
        const predictionId = button.dataset.predictionId;

        if (!confirm('Are you sure you want to delete this career prediction?')) {
            return;
        }

        try {
            await ApiService.fetchApi(`/api/career-predictions/${predictionId}/`, 'DELETE');
            UiUtils.showToast('Career prediction deleted successfully!', 'success');
            button.closest('.col-lg-6').remove();
        } catch (error) {
            // Error handling is done inside ApiService.fetchApi
        }
    }

    return {
        getRecommendations,
        saveCareerPrediction,
        fetchAndDisplaySavedCareers,
        deleteSavedPrediction
    };
})();

// =====================================
// Initialization
// =====================================
// This section sets up the main event listeners for the page.
document.addEventListener('DOMContentLoaded', () => {
    // Event listener for the form submission
    const form = document.getElementById('prediction-form');
    if (form) {
        form.addEventListener('submit', CareerModule.getRecommendations);
    }

    // Event listener for the "Saved Recommendations" tab
    const savedTab = document.getElementById('saved-tab');
    if (savedTab) {
        savedTab.addEventListener('shown.bs.tab', CareerModule.fetchAndDisplaySavedCareers);
    }

    // Event listener for the "Refresh" button on the saved tab
    const refreshBtn = document.getElementById('refresh-saved');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', CareerModule.fetchAndDisplaySavedCareers);
    }
});
