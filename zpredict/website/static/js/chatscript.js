 const chatMessages = document.getElementById('chatMessages');
        const questionInput = document.getElementById('question');
        const sendBtn = document.getElementById('sendBtn');

        // Auto-resize textarea
        questionInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });

        // Send on Enter (but not Shift+Enter)
        questionInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        sendBtn.addEventListener('click', sendMessage);

        function addMessage(content, isUser = false) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isUser ? 'user' : 'ai'}`;

            const now = new Date();
            const timeString = now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

            messageDiv.innerHTML = `
                <div class="message-bubble">
                    ${content}
                </div>
                <div class="message-time">${timeString}</div>
            `;

            // Remove welcome message on first interaction
            const welcomeMsg = chatMessages.querySelector('.welcome-message');
            if (welcomeMsg) {
                welcomeMsg.remove();
            }

            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        function setLoading(isLoading) {
            sendBtn.disabled = isLoading;
            if (isLoading) {
                sendBtn.classList.add('loading');
                sendBtn.innerHTML = 'Thinking<span class="loading-dots">•</span>';
            } else {
                sendBtn.classList.remove('loading');
                sendBtn.innerHTML = 'Send';
            }
        }

        async function sendMessage() {
            const question = questionInput.value.trim();
            if (!question) return;

            if (!isAuthenticated()) {
                addMessage("You need to log in first! Redirecting...", false);
                setTimeout(() => {
                    window.location.href = "/login/";
                }, 1500);
                return;
            }

            // Add user message
            addMessage(question, true);
            questionInput.value = '';
            questionInput.style.height = 'auto';
            setLoading(true);

            try {
                const response = await authenticatedFetch('http://127.0.0.1:8000/api/chat/', {
                    method: 'POST',
                    body: JSON.stringify({ question: question })
                });

                const data = await response.json();

                if (response.ok) {
                    addMessage(data.answer || "I got your message but I'm not sure how to respond to that!", false);
                } else {
                    const errorMsg = data.detail || "Something went wrong - Try Again!";
                    addMessage(`${errorMsg}`, false);
                }
            } catch (err) {
                if (err.message.includes('Authentication failed')) {
                    addMessage("Session expired! Please log in again.", false);
                    setTimeout(() => {
                        window.location.href = "/login/";
                    }, 1500);
                } else {
                    addMessage(`Connection error: ${err.message}. Don't worry, we'll figure it out!`, false);
                }
            } finally {
                setLoading(false);
                questionInput.focus();
            }
        }

        // Focus on input when page loads
        window.addEventListener('load', () => {
            questionInput.focus();
        });

        // Add some random particles periodically
        setInterval(() => {
            const particle = document.createElement('div');
            particle.className = 'particle';
            particle.style.left = Math.random() * 100 + '%';
            particle.style.animationDelay = '0s';
            document.querySelector('.particles').appendChild(particle);

            // Remove particle after animation
            setTimeout(() => {
                particle.remove();
            }, 25000);
        }, 3000);