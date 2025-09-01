//--------------------------------
// Design Elements for signup.html
//--------------------------------
// signupscript.js
document.addEventListener('DOMContentLoaded', function() {
    // Create particle background
    const particlesContainer = document.createElement('div');
    particlesContainer.classList.add('particles');
    document.body.appendChild(particlesContainer);
    
    const colors = ['#6C63FF', '#FF6B8B', '#36D6C3', '#FFC75F'];
    
    for (let i = 0; i < 20; i++) {
        const particle = document.createElement('div');
        particle.classList.add('particle');
        
        // Random properties
        const size = Math.random() * 20 + 5;
        const color = colors[Math.floor(Math.random() * colors.length)];
        
        particle.style.width = `${size}px`;
        particle.style.height = `${size}px`;
        particle.style.background = color;
        particle.style.top = `${Math.random() * 100}vh`;
        particle.style.left = `${Math.random() * 100}vw`;
        particle.style.animationDuration = `${Math.random() * 20 + 10}s`;
        particle.style.animationDelay = `${Math.random() * 5}s`;
        
        particlesContainer.appendChild(particle);
    }
    
    // Initialize form functionality
    initForm();
});

function initForm() {
    const form = document.getElementById('registerForm');
    if (!form) {
        console.error("Form with ID 'registerForm' not found!");
        return;
    }
    
    const progressFill = document.getElementById('progressFill');
    const statusDiv = document.getElementById('status');
    const submitBtn = document.getElementById('submitBtn');
    
    // Track form completion
    const inputs = form.querySelectorAll('.form-input');
    
    function updateProgress() {
        const filledInputs = Array.from(inputs).filter(input => input.value.trim() !== '');
        const progress = (filledInputs.length / inputs.length) * 100;
        if (progressFill) {
            progressFill.style.width = progress + '%';
        }
    }
    
    //------------------------------------
    // Functional Elements for signup.html   
    //------------------------------------
    
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
        if (submitBtn) {
            submitBtn.innerHTML = 'Loading...';
            submitBtn.disabled = true;
        }
        
        try {
            const response = await fetch('http://127.0.0.1:8000/api/register/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ first_name, last_name, email, password })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                if (statusDiv) {
                    statusDiv.className = 'status success';
                    statusDiv.innerHTML = 'You\'re in! Redirecting to login...';
                }
                
                setTimeout(() => {
                    window.location.href = "http://127.0.0.1:8000/website/login/";
                }, 1500);
            } else {
                if (statusDiv) {
                    statusDiv.className = 'status error';
                    statusDiv.innerHTML = (data.detail || 'Registration failed. Try again!');
                }
            }
        } catch (err) {
            if (statusDiv) {
                statusDiv.className = 'status error';
                statusDiv.innerHTML = 'Connection error: ' + err.message;
            }
        } finally {
            if (submitBtn) {
                submitBtn.innerHTML = 'Start Your Journey';
                submitBtn.disabled = false;
            }
        }
    });
    
    // Initial progress update
    updateProgress();
}