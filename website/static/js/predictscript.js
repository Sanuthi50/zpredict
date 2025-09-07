// -------------------------------
// Configuration Module (config.js)
// -------------------------------
const Config = {
    BASE_URL: '', // Your Django base URL
    getToken: () => localStorage.getItem('access_token'),
    getCSRFToken: () => {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        return cookieValue || '';
    }
};

// -------------------------------
// Utility Functions Module (utils.js)
// -------------------------------
const Utils = {
    escapeHtml: (text) => {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    truncateText: (text, maxLength) => {
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    },

    getConfidenceClass: (confidence) => {
        if (!confidence) return '';
        if (confidence >= 0.7) return 'confidence-high';
        if (confidence >= 0.5) return 'confidence-medium';
        return 'confidence-low';
    },

    getRecommendationClass: (recommendation) => {
        switch (recommendation) {
            case 'Highly Recommended': return 'highly-recommended';
            case 'Recommended': return 'recommended';
            case 'Not Recommended': return 'not-recommended';
            default: return '';
        }
    },

    showNotification: (message, type = 'info', duration = 5000) => {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px;
            border-radius: 5px;
            color: white;
            z-index: 10000;
            opacity: 0;
            transition: opacity 0.3s;
        `;
        
        // Style based on type
        if (type === 'error') notification.style.backgroundColor = '#FF8066';
        else if (type === 'success') notification.style.backgroundColor = '#00C9A7';
        else notification.style.backgroundColor = '#6C63FF';
        
        // Add to DOM
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => notification.style.opacity = 1, 10);
        
        // Remove after duration
        setTimeout(() => {
            notification.style.opacity = 0;
            setTimeout(() => notification.remove(), 300);
        }, duration);
    }
};

// -------------------------------
// API Service Module (api-service.js)
// -------------------------------
const ApiService = (() => {
    // Helper function to handle API responses
    const handleResponse = async (response) => {
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        return response.json();
    };

    // Handle API errors
    const handleApiError = (response, data) => {
        let errorMessage = "An unexpected error occurred.";
        
        if (data && data.error) {
            errorMessage = data.error;
        } else if (response.status === 401) {
            errorMessage = "Your session has expired. Please login again.";
            // Redirect to login after a delay
            setTimeout(() => {
                window.location.href = "/website/login/";
            }, 2000);
        } else if (response.status === 403) {
            errorMessage = "You don't have permission to access this feature.";
        } else if (response.status === 429) {
            errorMessage = "Too many requests. Please try again later.";
        } else if (response.status === 503) {
            errorMessage = "Prediction service is currently unavailable. Please try again later.";
        }
        
        return errorMessage;
    };

    return {
        // Get prediction from ML model
        getPrediction: async (predictionData) => {
            const token = Config.getToken();
            if (!token) {
                throw new Error("Please login first to access predictions.");
            }

            const response = await fetch(`${Config.BASE_URL}/api/predictions/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(predictionData)
            });

            const data = await response.json();
            
            if (!response.ok) {
                const errorMessage = handleApiError(response, data);
                throw new Error(errorMessage);
            }
            
            return data;
        },

        // Save selected predictions
        savePredictions: async (sessionId, predictions) => {
            const token = Config.getToken();
            if (!token) {
                throw new Error("Please login first.");
            }

            const response = await fetch(`${Config.BASE_URL}/api/predictions/save/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    selected_predictions: predictions
                })
            });

            const data = await response.json();
            
            if (!response.ok) {
                const errorMessage = handleApiError(response, data);
                throw new Error(errorMessage);
            }
            
            return data;
        },

        // Get prediction history
        getPredictionHistory: async () => {
            const token = Config.getToken();
            if (!token) {
                throw new Error("Please login first.");
            }

            const response = await fetch(`${Config.BASE_URL}/api/predictions/history/`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            const data = await response.json();
            
            if (!response.ok) {
                const errorMessage = handleApiError(response, data);
                throw new Error(errorMessage);
            }
            
            return data;
        },

        // Get saved predictions
        getSavedPredictions: async () => {
            const token = Config.getToken();
            if (!token) {
                throw new Error("Please login first.");
            }

            const response = await fetch(`${Config.BASE_URL}/api/saved-predictions/my_predictions/`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error('Saved predictions error:', response.status, errorText);
                throw new Error(`Failed to load saved predictions: ${response.status}`);
            }

            const data = await response.json();
            return data;
        },

        // Delete a saved prediction
        deleteSavedPrediction: async (predictionId) => {
            const token = Config.getToken();
            if (!token) {
                throw new Error("Please login first.");
            }

            const response = await fetch(`${Config.BASE_URL}/api/saved-predictions/${predictionId}/`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                const errorMessage = handleApiError(response, errorData);
                throw new Error(errorMessage);
            }
            
            return { success: true };
        },

        // Update a saved prediction (notes)
        updateSavedPrediction: async (predictionId, updateData) => {
            const token = Config.getToken();
            if (!token) {
                throw new Error("Please login first.");
            }

            const response = await fetch(`${Config.BASE_URL}/api/saved-predictions/${predictionId}/`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(updateData)
            });

            const data = await response.json();
            
            if (!response.ok) {
                const errorMessage = handleApiError(response, data);
                throw new Error(errorMessage);
            }
            
            return data;
        }
    };
})();

// -------------------------------
// UI Controller Module (ui-controller.js)
// -------------------------------
const UIController = (() => {
    // DOM Elements
    const elements = {
        inputForm: document.getElementById('input-form'),
        predictionsSection: document.getElementById('predictions-section'),
        savedPredictionsSection: document.getElementById('saved-predictions-section'),
        historySection: document.getElementById('history-section'),
        predictBtn: document.getElementById('predict-btn'),
        loadingMessage: document.getElementById('loading-message'),
        errorMessage: document.getElementById('error-message'),
        successMessage: document.getElementById('success-message'),
        predictionsTable: document.getElementById('predictions-table'),
        savedPredictionsTable: document.getElementById('saved-predictions-table'),
        historyList: document.getElementById('history-list'),
        progressBar: document.getElementById('progressBar'),
        funFact: document.getElementById('fun-fact')
    };

    // Form validation functions
    const validateForm = () => {
        const year = document.getElementById('year').value;
        const zScore = document.getElementById('z_score').value;
        const stream = document.getElementById('stream').value;
        const district = document.getElementById('district').value;
        
        let isValid = true;
        
        // Validate year
        if (!year || year < 2000 || year > 2030) {
            showValidationError('yearIcon', 'Please enter a valid year between 2000 and 2030');
            isValid = false;
        } else {
            showValidationSuccess('yearIcon');
        }
        
        // Validate Z-score
        if (!zScore || zScore < 0 || zScore > 3) {
            showValidationError('zScoreIcon', 'Please enter a valid Z-score between 0.000 and 3.000');
            isValid = false;
        } else {
            showValidationSuccess('zScoreIcon');
        }
        
        // Validate stream
        if (!stream) {
            showValidationError('streamIcon', 'Please select your field of study');
            isValid = false;
        } else {
            showValidationSuccess('streamIcon');
        }
        
        // Validate district
        if (!district) {
            showValidationError('districtIcon', 'Please select your district');
            isValid = false;
        } else {
            showValidationSuccess('districtIcon');
        }
        
        return isValid ? {
            year: parseInt(year),
            z_score: parseFloat(zScore),
            stream: stream,
            district: district,
            top_n: 100
        } : null;
    };

    const showValidationError = (iconId, message) => {
        const icon = document.getElementById(iconId);
        icon.style.backgroundColor = '#FF8066';
        icon.title = message;
    };

    const showValidationSuccess = (iconId) => {
        const icon = document.getElementById(iconId);
        icon.style.backgroundColor = '#00C9A7';
        icon.title = '';
    };

    // Show/hide sections
    const showSection = (section) => {
        elements.inputForm.classList.add('hidden');
        elements.predictionsSection.classList.add('hidden');
        elements.savedPredictionsSection.classList.add('hidden');
        elements.historySection.classList.add('hidden');
        
        section.classList.remove('hidden');
    };

    // Show loading state
    const showLoading = () => {
        elements.loadingMessage.classList.remove('hidden');
        elements.predictBtn.disabled = true;
        elements.predictBtn.querySelector('#btn-text').textContent = 'Processing...';
    };

    // Hide loading state
    const hideLoading = () => {
        elements.loadingMessage.classList.add('hidden');
        elements.predictBtn.disabled = false;
        elements.predictBtn.querySelector('#btn-text').textContent = 'Generate Predictions';
    };

    // Show error message
    const showError = (message) => {
        elements.errorMessage.textContent = message;
        elements.errorMessage.classList.remove('hidden');
        setTimeout(() => {
            elements.errorMessage.classList.add('hidden');
        }, 5000);
    };

    // Show success message
    const showSuccess = (message) => {
        elements.successMessage.textContent = message;
        elements.successMessage.classList.remove('hidden');
        setTimeout(() => {
            elements.successMessage.classList.add('hidden');
        }, 5000);
    };

    // Update progress bar
    const updateProgress = (percentage) => {
        elements.progressBar.style.width = `${percentage}%`;
    };

    // Calculate confidence score based on probability and other factors
    const calculateConfidenceScore = (prediction) => {
        let confidence = 0.5; // Base confidence
        
        // Adjust based on probability
        if (prediction.predicted_probability >= 0.8) confidence += 0.3;
        else if (prediction.predicted_probability >= 0.6) confidence += 0.2;
        else if (prediction.predicted_probability >= 0.4) confidence += 0.1;
        
        // Adjust based on recommendation
        if (prediction.recommendation === 'Highly Recommended') confidence += 0.2;
        else if (prediction.recommendation === 'Recommended') confidence += 0.1;
        
        return Math.min(confidence, 1.0);
    };

    // Display predictions in table
    const displayPredictions = (data) => {
        // Update session info
        const sessionInfo = document.getElementById('session-info');
        sessionInfo.innerHTML = `
            <strong>Session ID:</strong> ${data.session_id} | 
            <strong>Total Predictions:</strong> ${data.total_predictions} | 
            <strong>Confidence Level:</strong> ${data.confidence_level || 'High'} | 
            <strong>Generated:</strong> ${data.generated_at ? new Date(data.generated_at).toLocaleString() : 'Now'}
        `;

        // Prefer explicit unique lists from API; fallback to 'predictions'
        const coursePredictions = (data.unique_courses && data.unique_courses.length) ? data.unique_courses : (data.predictions || []);
        const universityPredictions = data.unique_universities || [];

        // Add confidence scores to predictions
        coursePredictions.forEach(pred => {
            pred.confidence_score = calculateConfidenceScore(pred);
        });
        
        if (universityPredictions.length > 0) {
            universityPredictions.forEach(pred => {
                pred.confidence_score = calculateConfidenceScore(pred);
            });
        }

        // Store in PredictionManager
        PredictionManager.setPredictions(coursePredictions, universityPredictions, data.session_id);
        
        // Populate filter dropdowns
        populateFilterDropdowns(coursePredictions);
        
        // Render the table
        PredictionManager.renderPredictionsTable();
        
        // Update stats
        updatePredictionStats(coursePredictions);
        
        // Show predictions section
        showSection(elements.predictionsSection);
    };

    const updatePredictionStats = (predictions) => {
        const total = predictions.length;
        const highlyRecommended = predictions.filter(p => p.recommendation === 'High Chance').length;
        const recommended = predictions.filter(p => p.recommendation === 'Moderate Chance').length;
        const avgProbability = predictions.length > 0 ? 
            (predictions.reduce((sum, p) => sum + p.predicted_probability, 0) / predictions.length) : 0;

        document.getElementById('total-predictions').textContent = total;
        document.getElementById('highly-recommended-count').textContent = highlyRecommended;
        document.getElementById('recommended-count').textContent = recommended;
        document.getElementById('avg-probability').textContent = (avgProbability * 100).toFixed(1) + '%';
    };

    // Populate filter dropdowns with available options
    const populateFilterDropdowns = (predictions) => {
        // Get unique courses and universities
        const uniqueCourses = [...new Set(predictions.map(p => p.course_name))].sort();
        const uniqueUniversities = [...new Set(predictions.map(p => p.university_name))].sort();
        
        // Populate course filter
        const courseFilter = document.getElementById('course-filter');
        if (courseFilter) {
            courseFilter.innerHTML = '<option value="">All Courses</option>';
            uniqueCourses.forEach(course => {
                const option = document.createElement('option');
                option.value = course;
                option.textContent = course;
                courseFilter.appendChild(option);
            });
        }
        
        // Populate university filter
        const universityFilter = document.getElementById('university-filter');
        if (universityFilter) {
            universityFilter.innerHTML = '<option value="">All Universities</option>';
            uniqueUniversities.forEach(university => {
                const option = document.createElement('option');
                option.value = university;
                option.textContent = university;
                universityFilter.appendChild(option);
            });
        }
    };

    // Display saved predictions
    const displaySavedPredictions = (data) => {
        const predictions = Array.isArray(data) ? data : (data.results || data.predictions || []);
        const tbody = elements.savedPredictionsTable.querySelector('tbody');
        tbody.innerHTML = '';
        
        if (predictions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No saved predictions found</td></tr>';
            showSection(elements.savedPredictionsSection);
            return;
        }
        
        predictions.forEach(prediction => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${prediction.university_name}</td>
                <td>${prediction.course_name}</td>
                <td>${prediction.predicted_cutoff}</td>
                <td>${(prediction.predicted_probability * 100).toFixed(1)}%</td>
                <td>${prediction.recommendation}</td>
                <td>${new Date(prediction.saved_at).toLocaleDateString()}</td>
                <td>${prediction.notes || '-'}</td>
                <td>
                    <button class="btn-small edit-notes" data-id="${prediction.id}">Edit Notes</button>
                    <button class="btn-small btn-danger delete-prediction" data-id="${prediction.id}">Delete</button>
                </td>
            `;
            tbody.appendChild(row);
        });
        
        // Show saved predictions section
        showSection(elements.savedPredictionsSection);
    };

    // Display prediction history
    const displayPredictionHistory = (history) => {
        const historyList = elements.historyList;
        historyList.innerHTML = '';
        
        if (history.length === 0) {
            historyList.innerHTML = '<li>No prediction history found</li>';
            return;
        }
        
        history.forEach(session => {
            const li = document.createElement('li');
            li.innerHTML = `
                <div class="history-item">
                    <h4>Session from ${new Date(session.predicted_at).toLocaleDateString()}</h4>
                    <p>Year: ${session.year} | Z-Score: ${session.z_score} | Stream: ${session.stream}</p>
                    <p>District: ${session.district} | Predictions: ${session.total_predictions_generated}</p>
                    <button class="btn-small view-session" data-id="${session.id}">View Details</button>
                </div>
            `;
            historyList.appendChild(li);
        });
        
        // Show history section
        showSection(elements.historySection);
    };

    return {
        elements,
        validateForm,
        showSection,
        displayPredictions,
        displaySavedPredictions,
        displayPredictionHistory,
        showLoading,
        hideLoading,
        showError,
        showSuccess,
        updateProgress
    };
})();

// -------------------------------
// Prediction Manager Module (prediction-manager.js)
// -------------------------------
const PredictionManager = (() => {
    let currentSessionId = null;
    let currentView = 'courses'; // 'courses' | 'universities'
    let coursePredictions = [];
    let universityPredictions = [];
    let allPredictions = [];
    let filteredPredictions = [];
    
    // Set predictions data
    const setPredictions = (courses, universities, sessionId) => {
        coursePredictions = courses;
        universityPredictions = universities;
        currentSessionId = sessionId;
        allPredictions = (currentView === 'universities') ? universityPredictions : coursePredictions;
        filteredPredictions = [...allPredictions];
    };

    // Render predictions table
    const renderPredictionsTable = () => {
        const tbody = document.querySelector('#predictions-table tbody');
        tbody.innerHTML = '';

        filteredPredictions.forEach((pred, index) => {
            const tr = document.createElement('tr');
            
            // Apply confidence-based styling
            const confidenceClass = Utils.getConfidenceClass(pred.confidence_score);
            tr.className = confidenceClass;
            
            const recommendationClass = Utils.getRecommendationClass(pred.recommendation);
            
            tr.innerHTML = `
                <td><input type="checkbox" class="select-prediction" data-index="${index}" 
                           data-university="${Utils.escapeHtml(pred.university_name)}" 
                           data-course="${Utils.escapeHtml(pred.course_name)}" 
                           data-cutoff="${pred.predicted_cutoff}" 
                           data-probability="${pred.predicted_probability}" 
                           data-aptitude="${pred.aptitude_test_required || false}" 
                           data-merit="${pred.all_island_merit || true}"
                           data-recommendation="${Utils.escapeHtml(pred.recommendation)}"
                           data-confidence="${pred.confidence_score || 0.5}"></td>
                <td title="${Utils.escapeHtml(pred.university_name)}">${Utils.truncateText(pred.university_name, 30)}</td>
                <td title="${Utils.escapeHtml(pred.course_name)}">${Utils.truncateText(pred.course_name, 40)}</td>
                <td>${pred.predicted_cutoff}</td>
                <td>${(pred.predicted_probability * 100).toFixed(1)}%</td>
                <td class="recommendation ${recommendationClass}">${pred.recommendation}</td>
                <td>${pred.confidence_score ? (pred.confidence_score * 100).toFixed(0) + '%' : 'N/A'}</td>
                <td>${pred.aptitude_test_required ? 'Yes' : 'No'}</td>
                <td>${pred.all_island_merit ? 'Yes' : 'No'}</td>
            `;
            tbody.appendChild(tr);
        });

        // Add event listeners for checkboxes
        document.querySelectorAll('.select-prediction').forEach(checkbox => {
            checkbox.addEventListener('change', updateSelectionCount);
        });
    };

    // Update selection count
    const updateSelectionCount = () => {
        const selectedCount = document.querySelectorAll('.select-prediction:checked').length;
        document.getElementById('selection-count').textContent = `${selectedCount} predictions selected`;
    };

    // Get selected predictions
    const getSelectedPredictions = () => {
        const checkboxes = document.querySelectorAll('.select-prediction:checked');
        return Array.from(checkboxes).map(cb => ({
            university_name: cb.dataset.university,
            course_name: cb.dataset.course,
            predicted_cutoff: parseFloat(cb.dataset.cutoff),
            predicted_probability: parseFloat(cb.dataset.probability),
            aptitude_test_required: cb.dataset.aptitude === 'true',
            all_island_merit: cb.dataset.merit === 'true',
            recommendation: cb.dataset.recommendation,
            confidence_score: parseFloat(cb.dataset.confidence) || 0.5
        }));
    };

    // Selection controls
    const selectAll = () => {
        document.querySelectorAll('.select-prediction').forEach(cb => {
            cb.checked = true;
        });
        updateSelectionCount();
    };

    const selectNone = () => {
        document.querySelectorAll('.select-prediction').forEach(cb => {
            cb.checked = false;
        });
        updateSelectionCount();
    };

    const selectRecommended = () => {
        document.querySelectorAll('.select-prediction').forEach(cb => {
            const recommendation = cb.dataset.recommendation;
            cb.checked = recommendation === 'High Chance' || recommendation === 'Moderate Chance';
        });
        updateSelectionCount();
    };

    // Filter predictions
    const filterPredictions = () => {
        const searchTerm = document.getElementById('search-filter').value.toLowerCase();
        const courseFilter = document.getElementById('course-filter').value;
        const universityFilter = document.getElementById('university-filter').value;
        const recommendationFilter = document.getElementById('recommendation-filter').value;
        
        filteredPredictions = allPredictions.filter(pred => {
            // Search filter
            const matchesSearch = !searchTerm || 
                pred.university_name.toLowerCase().includes(searchTerm) ||
                pred.course_name.toLowerCase().includes(searchTerm) ||
                pred.recommendation.toLowerCase().includes(searchTerm);
            
            // Course filter
            const matchesCourse = !courseFilter || pred.course_name === courseFilter;
            
            // University filter
            const matchesUniversity = !universityFilter || pred.university_name === universityFilter;
            
            // Recommendation filter
            const matchesRecommendation = !recommendationFilter || pred.recommendation === recommendationFilter;
            
            return matchesSearch && matchesCourse && matchesUniversity && matchesRecommendation;
        });
        
        renderPredictionsTable();
        updateSelectionCount();
    };

    // Switch view between courses and universities
    const switchView = (view) => {
        currentView = view;
        allPredictions = (view === 'universities') ? universityPredictions : coursePredictions;
        filteredPredictions = [...allPredictions];
        renderPredictionsTable();
        updateSelectionCount();
        
        // Update prediction stats
        const total = allPredictions.length;
        const highlyRecommended = allPredictions.filter(p => p.recommendation === 'Highly Recommended').length;
        const recommended = allPredictions.filter(p => p.recommendation === 'Recommended').length;
        const avgProbability = allPredictions.length > 0 ? 
            (allPredictions.reduce((sum, p) => sum + p.predicted_probability, 0) / allPredictions.length) : 0;

        document.getElementById('total-predictions').textContent = total;
        document.getElementById('highly-recommended-count').textContent = highlyRecommended;
        document.getElementById('recommended-count').textContent = recommended;
        document.getElementById('avg-probability').textContent = (avgProbability * 100).toFixed(1) + '%';
    };

    return {
        setPredictions,
        renderPredictionsTable,
        updateSelectionCount,
        getSelectedPredictions,
        selectAll,
        selectNone,
        selectRecommended,
        filterPredictions,
        switchView,
        getCurrentSessionId: () => currentSessionId
    };
})();

// -------------------------------
// Event Handlers Module (event-handlers.js)
// -------------------------------
const EventHandlers = (() => {
    const init = () => {
        const { elements } = UIController;
        
        // Generate predictions button
        if (elements.predictBtn) {
            elements.predictBtn.addEventListener('click', handlePredictionRequest);
        }
        
        // Save selected predictions button
        const saveSelectedBtn = document.getElementById('save-selected-btn');
        if (saveSelectedBtn) {
            saveSelectedBtn.addEventListener('click', handleSaveSelected);
        }
        
        // View saved predictions button
        const viewSavedBtn = document.getElementById('view-saved-btn');
        if (viewSavedBtn) {
            viewSavedBtn.addEventListener('click', handleViewSaved);
        }
        
        // View history button
        const viewHistoryBtn = document.getElementById('view-history-btn');
        if (viewHistoryBtn) {
            viewHistoryBtn.addEventListener('click', handleViewHistory);
        }
        
        // Selection controls
        const selectAllBtn = document.getElementById('select-all-btn');
        if (selectAllBtn) {
            selectAllBtn.addEventListener('click', PredictionManager.selectAll);
        }
        
        const selectNoneBtn = document.getElementById('select-none-btn');
        if (selectNoneBtn) {
            selectNoneBtn.addEventListener('click', PredictionManager.selectNone);
        }
        
        const selectRecommendedBtn = document.getElementById('select-recommended-btn');
        if (selectRecommendedBtn) {
            selectRecommendedBtn.addEventListener('click', PredictionManager.selectRecommended);
        }
        
        // Filter controls
        const searchFilter = document.getElementById('search-filter');
        if (searchFilter) {
            searchFilter.addEventListener('input', PredictionManager.filterPredictions);
        }
        
        const courseFilter = document.getElementById('course-filter');
        if (courseFilter) {
            courseFilter.addEventListener('change', PredictionManager.filterPredictions);
        }
        
        const universityFilter = document.getElementById('university-filter');
        if (universityFilter) {
            universityFilter.addEventListener('change', PredictionManager.filterPredictions);
        }
        
        const recommendationFilter = document.getElementById('recommendation-filter');
        if (recommendationFilter) {
            recommendationFilter.addEventListener('change', PredictionManager.filterPredictions);
        }
        
        // View controls
        const viewCoursesBtn = document.getElementById('view-courses-btn');
        if (viewCoursesBtn) {
            viewCoursesBtn.addEventListener('click', () => PredictionManager.switchView('courses'));
        }
        
        const viewUniversitiesBtn = document.getElementById('view-universities-btn');
        if (viewUniversitiesBtn) {
            viewUniversitiesBtn.addEventListener('click', () => PredictionManager.switchView('universities'));
        }
        
        // Delegated event listeners for dynamic content
        document.addEventListener('click', handleDelegatedEvents);
    };
    
    const handlePredictionRequest = async () => {
        const formData = UIController.validateForm();
        if (!formData) return;
        
        try {
            UIController.showLoading();
            UIController.updateProgress(30);
            
            const response = await ApiService.getPrediction(formData);
            
            UIController.updateProgress(90);
            UIController.displayPredictions(response);
            
            UIController.updateProgress(100);
            setTimeout(() => UIController.updateProgress(0), 1000);
            
            Utils.showNotification(`Successfully generated ${response.total_predictions} predictions!`, 'success');
        } catch (error) {
            UIController.showError(error.message);
            console.error('Prediction error:', error);
        } finally {
            UIController.hideLoading();
        }
    };
    
    const handleSaveSelected = async () => {
        const selectedPredictions = PredictionManager.getSelectedPredictions();
        const sessionId = PredictionManager.getCurrentSessionId();
        
        if (!selectedPredictions.length) {
            UIController.showError("Please select at least one prediction to save.");
            return;
        }

        if (!sessionId) {
            UIController.showError("No active prediction session. Please generate predictions first.");
            return;
        }

        try {
            UIController.showLoading();
            const response = await ApiService.savePredictions(sessionId, selectedPredictions);
            
            Utils.showNotification(`${response.total_saved} predictions saved successfully!`, 'success');
            
            // Uncheck saved predictions
            document.querySelectorAll('.select-prediction:checked').forEach(cb => cb.checked = false);
            PredictionManager.updateSelectionCount();
        } catch (error) {
            UIController.showError(error.message);
            console.error('Save error:', error);
        } finally {
            UIController.hideLoading();
        }
    };
    
    const handleViewSaved = async () => {
        try {
            UIController.showLoading();
            const response = await ApiService.getSavedPredictions();
            UIController.displaySavedPredictions(response);
        } catch (error) {
            UIController.showError(error.message);
            console.error('Load saved error:', error);
        } finally {
            UIController.hideLoading();
        }
    };
    
    const handleViewHistory = async () => {
        try {
            UIController.showLoading();
            const response = await ApiService.getPredictionHistory();
            UIController.displayPredictionHistory(response.prediction_history || response);
        } catch (error) {
            UIController.showError(error.message);
            console.error('History error:', error);
        } finally {
            UIController.hideLoading();
        }
    };
    
    const handleDelegatedEvents = (event) => {
        // Delete prediction button
        if (event.target.classList.contains('delete-prediction')) {
            const predictionId = event.target.dataset.id;
            if (confirm('Are you sure you want to delete this saved prediction?')) {
                deleteSavedPrediction(predictionId);
            }
        }
        
        // Edit notes button
        if (event.target.classList.contains('edit-notes')) {
            const predictionId = event.target.dataset.id;
            const notes = prompt('Enter your notes:');
            if (notes !== null) {
                updatePredictionNotes(predictionId, notes);
            }
        }
        
        // View session details button
        if (event.target.classList.contains('view-session')) {
            const sessionId = event.target.dataset.id;
            alert(`Viewing session details for ID: ${sessionId}`);
            // Implement detailed view functionality here
        }
    };
    
    const deleteSavedPrediction = async (predictionId) => {
        try {
            UIController.showLoading();
            await ApiService.deleteSavedPrediction(predictionId);
            Utils.showNotification('Prediction deleted successfully!', 'success');
            // Reload saved predictions
            await handleViewSaved();
        } catch (error) {
            UIController.showError(error.message);
            console.error('Delete error:', error);
        } finally {
            UIController.hideLoading();
        }
    };
    
    const updatePredictionNotes = async (predictionId, notes) => {
        try {
            UIController.showLoading();
            await ApiService.updateSavedPrediction(predictionId, { notes });
            Utils.showNotification('Notes updated successfully!', 'success');
            // Reload saved predictions
            await handleViewSaved();
        } catch (error) {
            UIController.showError(error.message);
            console.error('Update notes error:', error);
        } finally {
            UIController.hideLoading();
        }
    };
    
    return { init };
})();

// -------------------------------
// Main Application Initialization
// -------------------------------
document.addEventListener('DOMContentLoaded', () => {
    // Check if user is logged in
    const token = Config.getToken();
    if (!token) {
        UIController.showError("Please login to access the prediction system.");
        // You might want to redirect to login page after a delay
        setTimeout(() => {
            window.location.href = "/website/login/";
        }, 3000);
        return;
    }
    
    // Initialize event handlers
    EventHandlers.init();
    
    // Set up periodic token validation (optional)
    setInterval(() => {
        if (!Config.getToken()) {
            UIController.showError("Your session has expired. Please login again.");
            setTimeout(() => {
                window.location.href = "/website/login/";
            }, 2000);
        }
    }, 300000); // Check every 5 minutes
});