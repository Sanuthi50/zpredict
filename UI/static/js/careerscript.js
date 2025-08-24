// Get JWT token from localStorage
function getToken() {
    return localStorage.getItem('access_token');
}

document.getElementById('get-recommendations').addEventListener('click', async () => {
    const degreeProgram = document.getElementById('degree-program').value;
    const recommendationsList = document.getElementById('recommendations-list');
    const errorMessage = document.getElementById('error-message');

    // Clear previous results and errors
    recommendationsList.innerHTML = '';
    errorMessage.textContent = '';

    if (!degreeProgram) {
        errorMessage.textContent = 'Please enter a degree program.';
        return;
    }

    // Get JWT token
    const token = getToken();
    if (!token) {
        errorMessage.textContent = 'Please log in to get recommendations.';
        return;
    }

    try {
        const response = await fetch('/api/recommendations/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ degree_program: degreeProgram }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Full API response:', data);
        const recommendations = data.recommendations || [];
        console.log('Recommendations array:', recommendations);
        
        if (recommendations.length > 0) {
            console.log('First recommendation object:', recommendations[0]);
            console.log('Properties of first recommendation:', Object.keys(recommendations[0]));
        }

        if (recommendations.length === 0) {
            recommendationsList.innerHTML = '<p>No recommendations found for this degree program.</p>';
        } else {
            recommendations.forEach(rec => {
                const recDiv = document.createElement('div');
                recDiv.classList.add('recommendation-item');
                recDiv.innerHTML = `
                    <h3>${rec.title || 'Career Title'}</h3>
                    <p><strong>Linked Sri Lankan Occupation:</strong> ${rec.occupation || 'N/A'}</p>
                    <p><strong>Number of Vacancies:</strong> ${rec.vacancies || 'N/A'}</p>
                    <p><strong>Combined Score:</strong> ${rec.combined_score ? rec.combined_score.toFixed(4) : 'N/A'}</p>
                    <p><strong>Similarity Score:</strong> ${rec.similarity_score ? rec.similarity_score.toFixed(4) : 'N/A'}</p>
                    ${rec['Skills'] && Array.isArray(rec['Skills']) ? `
                        <h4>Skills:</h4>
                        <ul>
                            ${rec['Skills'].map(skill => `<li>${skill['Element Name'] || skill['Element_Name'] || skill.name}: ${skill['Data Value'] ? skill['Data Value'].toFixed(2) : (skill['Data_Value'] ? skill['Data_Value'].toFixed(2) : skill.value)}</li>`).join('')}
                        </ul>
                    ` : ''}
                    ${rec['Abilities'] && Array.isArray(rec['Abilities']) ? `
                        <h4>Abilities:</h4>
                        <ul>
                            ${rec['Abilities'].map(ability => `<li>${ability['Element Name'] || ability['Element_Name'] || ability.name}: ${ability['Data Value'] ? ability['Data Value'].toFixed(2) : (ability['Data_Value'] ? ability['Data_Value'].toFixed(2) : ability.value)}</li>`).join('')}
                        </ul>
                    ` : ''}
                `;
                recommendationsList.appendChild(recDiv);
            });
        }

    } catch (error) {
        console.error('Error fetching recommendations:', error);
        errorMessage.textContent = `Error getting recommendations: ${error.message}`;
    }
});