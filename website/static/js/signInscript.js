//--------------------------------
// Design Elemets for signin.html
//--------------------------------
// signInscript.js
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
    
       
});
//--------------------------------
// Functional Elements for signin.html   
//--------------------------------
const form = document.getElementById('loginForm');
        const statusDiv = document.getElementById('status');
        const submitBtn = document.getElementById('submitBtn');
        
        //LOGIN LOGIC 
        document.getElementById('loginForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            
            // Enhanced button loading state
            submitBtn.innerHTML = 'Logging in... <span class="loading-animation"></span>';
            submitBtn.disabled = true;
            
            try {
                const response = await fetch('http://127.0.0.1:8000/api/login/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    //TOKEN STORAGE 
                    localStorage.setItem('access_token', data.access);
                    localStorage.setItem('refresh_token', data.refresh);
                    
                    statusDiv.className = 'status success';
                    statusDiv.innerText = "Login successful! Redirecting...";
                    
                    setTimeout(() => { 
                        window.location.href = "http://127.0.0.1:8000/website"; 
                    }, 1500);
                } else {
                    statusDiv.className = 'status error';
                    statusDiv.innerText = "ERROR: " + (data.detail || "Login failed");
                }
            } catch (err) {
                statusDiv.className = 'status error';
                statusDiv.innerText = "ERROR: " + err.message;
            } finally {
                // Reset button
                submitBtn.innerHTML = 'Let\'s Go!';
                submitBtn.disabled = false;
            }
        });
        