 // Base URL - Update if needed
 const API_BASE_URL = 'http://127.0.0.1:8000'; // Change to your backend domain if different

 document.getElementById('registerForm').addEventListener('submit', async function(e) {
   e.preventDefault(); // Prevent default form submission

   const email = document.getElementById('email').value.trim();
   const first_name = document.getElementById('first_name').value.trim();
   const last_name = document.getElementById('last_name').value.trim();
   const password = document.getElementById('password').value;
   const confirm_password = document.getElementById('confirm_password').value;

   const messageDiv = document.getElementById('message');
   const submitBtn = document.getElementById('submitBtn');

   // Clear previous messages
   messageDiv.innerHTML = '';

   // Client-side validation
   if (password !== confirm_password) {
     showMessage('Passwords do not match.', 'error');
     return;
   }

   if (password.length < 6) {
     showMessage('Password must be at least 6 characters.', 'error');
     return;
   }

   // Disable button during request
   submitBtn.disabled = true;
   submitBtn.textContent = 'Registering...';

   try {
     const response = await fetch('http://127.0.0.1:8000/api/admin/register/', {
       method: 'POST',
       headers: {
         'Content-Type': 'application/json',
       },
       body: JSON.stringify({
         email: email,
         first_name: first_name,
         last_name: last_name,
         password: password,
         confirm_password: confirm_password  
       })
     });

     if (response.ok) {
       const data = await response.json();
       showMessage('Registration successful! Redirecting to login...', 'success');
       // Optionally clear form
       setTimeout(() => { window.location.href = "http://127.0.0.1:8000/admin-dashboard/"; }, 1500);
     } else {
       // Try to get JSON error
       let errorMessage = 'Registration failed.';
       try {
         const errorData = await response.json();
         const errorKeys = Object.keys(errorData);
         if (errorKeys.includes('email')) {
           errorMessage = 'Email: ' + errorData.email.join(', ');
         } else if (errorKeys.includes('non_field_errors')) {
           errorMessage = errorData.non_field_errors.join(', ');
         } else {
           errorMessage = Object.values(errorData)[0];
         }
       } catch (e) {
         // Fallback: if response is not JSON
         const errorText = await response.text();
         console.warn("Server error (non-JSON):", errorText);
         errorMessage = 'Server error. Check console.';
       }
       showMessage(errorMessage, 'error');
     }
   } catch (error) {
     console.error('Network or server error:', error);
     showMessage('Unable to connect to server. Is it running?', 'error');
   } finally {
     submitBtn.disabled = false;
     submitBtn.textContent = 'Register Admin';
   }
 });

 // Utility to show messages
 function showMessage(text, type) {
   const messageDiv = document.getElementById('message');
   const alert = document.createElement('div');
   alert.className = `alert ${type}`;
   alert.textContent = text;
   messageDiv.innerHTML = '';
   messageDiv.appendChild(alert);

   setTimeout(() => {
     if (alert.parentElement) {
       alert.remove();
     }
   }, 5000);
 }