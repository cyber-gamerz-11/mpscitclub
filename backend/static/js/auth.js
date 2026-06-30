// Auth JS for MPSC IT CLUB

document.addEventListener('DOMContentLoaded', () => {
    
    const setButtonLoading = (btn, isLoading, originalText) => {
        if (isLoading) {
            btn.disabled = true;
            btn.innerHTML = `<span class="spinner"></span>Processing...`;
        } else {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    };
    
    // Signup Logic
    const signupForm = document.getElementById('signup-form');
    if (signupForm) {
        const btn = signupForm.querySelector('button[type="submit"]');
        const originalText = btn.innerHTML;

        signupForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            setButtonLoading(btn, true, originalText);
            const formData = new FormData(signupForm);
            
            try {
                const response = await fetch('/auth/signup', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                if (response.ok) {
                    window.showToast('Signup successful! Welcome to the club.', 'success');
                    setTimeout(() => {
                        window.location.href = '/auth/login';
                    }, 2000);
                } else {
                    window.showToast(data.error, 'error');
                    setButtonLoading(btn, false, originalText);
                }
            } catch (err) {
                console.error(err);
                window.showToast('Connection failed. Try again.', 'error');
                setButtonLoading(btn, false, originalText);
            }
        });
    }

    // Login Logic
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        const emailInput = document.getElementById('email');
        if (emailInput) {
            emailInput.value = localStorage.getItem('rememberedEmail') || '';
        }

        const btn = loginForm.querySelector('button[type="submit"]');
        const originalText = btn.innerHTML;

        const errorEl = document.getElementById('login-error');

        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (errorEl) errorEl.style.display = 'none'; // Clear previous errors
            setButtonLoading(btn, true, originalText);
            const formData = new FormData(loginForm);
            
            try {
                const response = await fetch('/auth/login', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                if (response.ok) {
                    // Remember email in browser localStorage
                    localStorage.setItem('rememberedEmail', formData.get('email'));
                    // Instant redirect on success
                    window.location.href = '/user/dashboard';
                } else {
                    if (errorEl) {
                        errorEl.innerText = data.error || 'Invalid email or password';
                        errorEl.style.display = 'block';
                    }
                    setButtonLoading(btn, false, originalText);
                }
            } catch (err) {
                console.error(err);
                if (errorEl) {
                    errorEl.innerText = 'Login failed. Please check your connection and try again.';
                    errorEl.style.display = 'block';
                }
                setButtonLoading(btn, false, originalText);
            }
        });
    }

    // Forgot Password Logic
    const forgotForm = document.getElementById('forgot-form');
    if (forgotForm) {
        const btn = forgotForm.querySelector('button[type="submit"]');
        const originalText = btn.innerHTML;

        forgotForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            setButtonLoading(btn, true, originalText);
            const formData = new FormData(forgotForm);

            try {
                const response = await fetch('/auth/forgot-password', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                if (response.ok) {
                    window.showToast('Reset link sent to your email!', 'success');
                    forgotForm.reset();
                } else {
                    window.showToast(data.error, 'error');
                }
            } catch (err) {
                window.showToast('Failed to send email.', 'error');
            } finally {
                setButtonLoading(btn, false, originalText);
            }
        });
    }
});
