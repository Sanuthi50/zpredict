const form = document.getElementById('loginForm');
        const statusDiv = document.getElementById('status');
        const submitBtn = document.getElementById('submitBtn');
        const funFact = document.getElementById('funFact');
                     
        // Add focus effects to inputs
        const inputs = form.querySelectorAll('.form-input');
        inputs.forEach(input => {
            input.addEventListener('focus', function() {
                this.parentElement.style.transform = 'scale(1.02)';
            });
            
            input.addEventListener('blur', function() {
                this.parentElement.style.transform = 'scale(1)';
            });
        });
        
        // ORIGINAL LOGIN LOGIC - PRESERVED EXACTLY
        document.getElementById('loginForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            
            // Enhanced button loading state
            submitBtn.innerHTML = 'Logging in... <span class="loading-animation">⏳</span>';
            submitBtn.disabled = true;
            
            try {
                const response = await fetch('http://127.0.0.1:8000/api/login/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    // ORIGINAL TOKEN STORAGE - UNCHANGED
                    localStorage.setItem('access_token', data.access);
                    localStorage.setItem('refresh_token', data.refresh);
                    
                    statusDiv.className = 'status success';
                    statusDiv.innerText = "✅ Login successful! Redirecting...";
                    
                    setTimeout(() => { 
                        window.location.href = "http://127.0.0.1:8000"; 
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
                submitBtn.innerHTML = 'Let\'s Go! 🚀';
                submitBtn.disabled = false;
            }
        });
        
        // Add some random particle positioning
        const particles = document.querySelectorAll('.particle');
        particles.forEach((particle, index) => {
            particle.style.top = Math.random() * 100 + '%';
            particle.style.animationDelay = -(Math.random() * 8) + 's';
        });