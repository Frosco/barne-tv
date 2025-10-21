/**
 * Admin interface entry point - authentication and management
 *
 * TIER 2 Rule 9: Always handle frontend fetch errors
 * TIER 3 Rule 14: Norwegian error messages for users
 * Security: Use textContent (not innerHTML) to prevent XSS
 */
import './main.css';
import { initChannelManagement } from './admin/channels.js';

console.log('Admin interface initialized');

// =============================================================================
// LOGIN FORM HANDLING (Story 1.4)
// =============================================================================

/**
 * Initialize login form if present on page.
 *
 * Sets up form submission handler with error handling and loading states.
 */
function initLoginForm() {
  const form = document.getElementById('login-form');
  if (!form) return; // Not on login page

  const passwordInput = document.getElementById('password');
  const loginButton = document.getElementById('login-button');
  const errorMessage = document.getElementById('error-message');

  form.addEventListener('submit', async (event) => {
    event.preventDefault();

    // Clear previous error
    errorMessage.style.display = 'none';
    errorMessage.textContent = '';

    // Get password value
    const password = passwordInput.value;

    // Disable button and show loading state
    loginButton.disabled = true;
    loginButton.textContent = 'Logger inn...';

    try {
      // TIER 2 Rule 9: Handle fetch errors
      const response = await fetch('/admin/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ password }),
      });

      if (!response.ok) {
        // Handle error response
        const data = await response.json();

        // TIER 3 Rule 14: Display Norwegian error message
        // Security: Use textContent (not innerHTML) to prevent XSS
        errorMessage.textContent = data.message || 'Noe gikk galt';
        errorMessage.style.display = 'block';

        // Re-enable button
        loginButton.disabled = false;
        loginButton.textContent = 'Logg inn';

        // Focus password field for retry
        passwordInput.select();
        return;
      }

      // Success - redirect to dashboard
      const data = await response.json();
      if (data.redirect) {
        window.location.href = data.redirect;
      } else {
        // Fallback redirect if no redirect URL provided
        window.location.href = '/admin/dashboard';
      }
    } catch (error) {
      // TIER 2 Rule 9: Handle network errors
      console.error('Login request failed:', error);

      // TIER 3 Rule 14: Norwegian generic error message
      errorMessage.textContent = 'Noe gikk galt';
      errorMessage.style.display = 'block';

      // Re-enable button
      loginButton.disabled = false;
      loginButton.textContent = 'Logg inn';
    }
  });

  // Focus password field on page load
  passwordInput.focus();
}

// =============================================================================
// PAGE INITIALIZATION
// =============================================================================

/**
 * Initialize appropriate page module based on current page.
 */
function initPage() {
  // Check which page we're on
  const path = window.location.pathname;

  if (path.includes('/admin/login')) {
    // Login page
    initLoginForm();
  } else if (path.includes('/admin/channels')) {
    // Channel management page (Story 1.5)
    initChannelManagement();
  } else if (path === '/admin' || path === '/admin/') {
    // Dashboard or default admin page - could redirect to channels
    // For now, assume it's the channels page
    initChannelManagement();
  }
}

// Initialize appropriate page on DOM load
document.addEventListener('DOMContentLoaded', initPage);
