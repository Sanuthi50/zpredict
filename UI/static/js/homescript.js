// Navigation function
function navigateTo(path) {
    console.log('Navigating to:', path);
    window.location.href = path;
}

// Create floating particles
function createParticles() {
    const container = document.getElementById('particles');
    if (!container) return;

    const particleCount = 50;
    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        const size = Math.random() * 5 + 2;
        particle.style.width = size + 'px';
        particle.style.height = size + 'px';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.top = Math.random() * 100 + '%';
        particle.style.animationDelay = Math.random() * 6 + 's';
        particle.style.animationDuration = (Math.random() * 3 + 4) + 's';
        container.appendChild(particle);
    }
}

// Navigation scroll effect
function handleScroll() {
    const navbar = document.getElementById('navbar');
    if (!navbar) return;

    if (window.scrollY > 50) {
        navbar.classList.add('scrolled');
    } else {
        navbar.classList.remove('scrolled');
    }
}

// Check authentication status and update UI
async function checkAuthStatus() {
    const token = localStorage.getItem('access_token');
    
    const authLink1 = document.getElementById('authLink1');
    const authLink2 = document.getElementById('authLink2');
    const logoutBtn = document.getElementById('logoutBtn');
    const userWelcome = document.getElementById('userWelcome');
    const welcomeText = document.getElementById('welcomeText');

    if (!authLink1 || !authLink2 || !logoutBtn || !userWelcome || !welcomeText) return;

    if (token) {
        try {
            const response = await fetch('http://127.0.0.1:8000/api/models/status/', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                authLink1.style.display = 'none';
                authLink2.style.display = 'none';
                logoutBtn.style.display = 'block';
                userWelcome.style.display = 'flex';
                welcomeText.textContent = 'Welcome back!';
            } else {
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                showLoginOptions();
            }
        } catch (error) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            showLoginOptions();
        }
    } else {
        showLoginOptions();
    }
}

function showLoginOptions() {
    const authLink1 = document.getElementById('authLink1');
    const authLink2 = document.getElementById('authLink2');
    const logoutBtn = document.getElementById('logoutBtn');
    const userWelcome = document.getElementById('userWelcome');

    if (!authLink1 || !authLink2 || !logoutBtn || !userWelcome) return;

    authLink1.style.display = 'block';
    authLink2.style.display = 'block';
    logoutBtn.style.display = 'none';
    userWelcome.style.display = 'none';
}

// Logout function
async function logout() {
    const logoutBtn = document.getElementById('logoutBtn');
    if (!logoutBtn) return;

    const originalText = logoutBtn.textContent;
    logoutBtn.textContent = 'Logging out... ⏳';
    logoutBtn.style.pointerEvents = 'none';
    logoutBtn.style.opacity = '0.7';

    try {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');

        logoutBtn.textContent = 'Logged out!';
        logoutBtn.style.background = 'rgba(16, 185, 129, 0.2)';
        logoutBtn.style.borderColor = '#10B981';
        logoutBtn.style.color = '#10B981';

        setTimeout(() => {
            checkAuthStatus();
            showLogoutMessage();
        }, 1000);
    } catch (error) {
        console.error('Logout error:', error);
        logoutBtn.textContent = originalText;
        logoutBtn.style.pointerEvents = 'auto';
        logoutBtn.style.opacity = '1';

        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        checkAuthStatus();
    }
}

// Stylish logout notification
function showLogoutMessage() {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 100px;
        right: 30px;
        background: rgba(26, 26, 46, 0.95);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(139, 92, 246, 0.3);
        border-radius: 15px;
        padding: 15px 20px;
        color: #E5E7EB;
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.9rem;
        z-index: 10000;
        animation: slideInRight 0.5s ease-out;
        box-shadow: 0 10px 30px rgba(139, 92, 246, 0.2);
    `;
    
    notification.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px;">
            <span>Successfully logged out! Come back soon!</span>
        </div>
    `;

    if (!document.querySelector('#logoutAnimations')) {
        const style = document.createElement('style');
        style.id = 'logoutAnimations';
        style.textContent = `
            @keyframes slideInRight {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes slideOutRight {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(100%); opacity: 0; }
            }
        `;
        document.head.appendChild(style);
    }

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.5s ease-in';
        setTimeout(() => notification.remove(), 500);
    }, 3000);
}

// Smooth scrolling
function smoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
}

// Init
document.addEventListener('DOMContentLoaded', function() {
    createParticles();
    smoothScroll();
    checkAuthStatus();

    setTimeout(() => document.body.classList.add('loading'), 100);
});

window.addEventListener('scroll', handleScroll);

// Feature card hover
document.querySelectorAll('.feature-card').forEach(card => {
    card.addEventListener('mouseenter', () => {
        card.style.transform = 'translateY(-10px) scale(1.02)';
    });
    card.addEventListener('mouseleave', () => {
        card.style.transform = 'translateY(0) scale(1)';
    });
});

// Continuous particle generation
setInterval(() => {
    const container = document.getElementById('particles');
    if (!container) return;

    const particle = document.createElement('div');
    particle.className = 'particle';
    const size = Math.random() * 5 + 2;
    particle.style.width = size + 'px';
    particle.style.height = size + 'px';
    particle.style.left = Math.random() * 100 + '%';
    particle.style.top = '100%';
    particle.style.animationDuration = (Math.random() * 3 + 4) + 's';
    container.appendChild(particle);

    setTimeout(() => particle.remove(), 8000);
}, 2000);

// Konami code Easter egg
let konamiCode = [];
const targetCode = ['ArrowUp','ArrowUp','ArrowDown','ArrowDown','ArrowLeft','ArrowRight','ArrowLeft','ArrowRight','b','a'];

document.addEventListener('keydown', function(e) {
    konamiCode.push(e.key);
    if (konamiCode.length > targetCode.length) konamiCode.shift();

    if (JSON.stringify(konamiCode) === JSON.stringify(targetCode)) {
        const container = document.getElementById('particles');
        if (!container) return;

        for (let i = 0; i < 30; i++) {
            setTimeout(() => {
                const particle = document.createElement('div');
                particle.className = 'particle';
                particle.style.width = '10px';
                particle.style.height = '10px';
                particle.style.left = '50%';
                particle.style.top = '50%';
                const color1 = Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0');
                const color2 = Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0');
                particle.style.background = `linear-gradient(45deg, #${color1}, #${color2})`;
                particle.style.animationDuration = '2s';
                container.appendChild(particle);
                setTimeout(() => particle.remove(), 2500);
            }, i * 50);
        }
        konamiCode = [];
    }
});
