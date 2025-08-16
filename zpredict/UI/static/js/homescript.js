
        // Create floating particles
        function createParticles() {
            const container = document.getElementById('particles');
            const particleCount = 50;

            for (let i = 0; i < particleCount; i++) {
                const particle = document.createElement('div');
                particle.className = 'particle';
                particle.style.width = Math.random() * 5 + 2 + 'px';
                particle.style.height = particle.style.width;
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
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        }

        // Navigation function
        function navigateTo(path) {
            window.location.href = `http://127.0.0.1:8000${path}`;
        }

        // Smooth scrolling for anchor links
        function smoothScroll() {
            document.querySelectorAll('a[href^="#"]').forEach(anchor => {
                anchor.addEventListener('click', function (e) {
                    e.preventDefault();
                    const target = document.querySelector(this.getAttribute('href'));
                    if (target) {
                        target.scrollIntoView({
                            behavior: 'smooth',
                            block: 'start'
                        });
                    }
                });
            });
        }

        // Initialize everything when page loads
        document.addEventListener('DOMContentLoaded', function() {
            createParticles();
            smoothScroll();
            
            // Add loading class to trigger final animations
            setTimeout(() => {
                document.body.classList.add('loading');
            }, 100);
        });

        // Listen for scroll events
        window.addEventListener('scroll', handleScroll);

        // Add some interactive hover effects
        document.querySelectorAll('.feature-card').forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-10px) scale(1.02) rotateX(5deg)';
            });
            
            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0) scale(1) rotateX(0deg)';
            });
        });

        // Enhanced CTA button interaction
        const ctaButton = document.querySelector('.cta-button');
        ctaButton.addEventListener('mouseenter', function() {
            this.style.background = 'linear-gradient(45deg, #ff8a80, #ff5722)';
        });
        
        ctaButton.addEventListener('mouseleave', function() {
            this.style.background = 'linear-gradient(45deg, #ff6b6b, #ee5a24)';
        });