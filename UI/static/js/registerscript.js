const form = document.getElementById('registerForm');
const progressFill = document.getElementById('progressFill');
const statusDiv = document.getElementById('status');
const submitBtn = document.getElementById('submitBtn');

// Track form completion
const inputs = form.querySelectorAll('.form-input');

function updateProgress() {
    const filledInputs = Array.from(inputs).filter(input => input.value.trim() !== '');
    const progress = (filledInputs.length / inputs.length) * 100;
    progressFill.style.width = progress + '%';
    
}

inputs.forEach(input => {
    input.addEventListener('input', updateProgress);
    
    // Add focus effects
    input.addEventListener('focus', function() {
        this.parentElement.style.transform = 'scale(1.02)';
    });
    
    input.addEventListener('blur', function() {
        this.parentElement.style.transform = 'scale(1)';
    });
});

form.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const first_name = document.getElementById('first_name').value;
    const last_name = document.getElementById('last_name').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    // Button loading state
    submitBtn.innerHTML = 'Loading... ⏳';
    submitBtn.disabled = true;
    
    try {
        const response = await fetch('http://127.0.0.1:8000/api/register/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ first_name, last_name, email, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            statusDiv.className = 'status success';
            statusDiv.innerHTML = '🎉 You\'re in! Redirecting to login... ✨';
            
            setTimeout(() => {
                window.location.href = "http://127.0.0.1:8000/login/";
            }, 1500);
        } else {
            statusDiv.className = 'status error';
            statusDiv.innerHTML = '⚠️ ' + (data.detail || 'Registration failed. Try again!');
        }
    } catch (err) {
        statusDiv.className = 'status error';
        statusDiv.innerHTML = '💀 Connection error: ' + err.message;
    } finally {
        submitBtn.innerHTML = 'Start Your Journey 🚀';
        submitBtn.disabled = false;
    }
});

// Add some random particle movement
const particles = document.querySelectorAll('.particle');
particles.forEach((particle, index) => {
    particle.style.top = Math.random() * 100 + '%';
    particle.style.animationDelay = -(Math.random() * 8) + 's';
});

// Initial progress update
updateProgress();