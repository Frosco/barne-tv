/**
 * Limit Reset Module (Story 4.1, Task 6)
 *
 * Handles:
 * - Daily limit reset confirmation dialog
 * - API call to reset endpoint
 * - Loading states and error handling
 * - Accessibility (keyboard nav, focus management, ARIA)
 */

/**
 * Initialize limit reset functionality.
 *
 * @param {Function} onSuccess - Callback function when reset succeeds (receives new limit data)
 */
export function initLimitReset(onSuccess) {
  const resetButton = document.getElementById('reset-limit-button');
  if (!resetButton) {
    return;
  }

  resetButton.addEventListener('click', () => {
    showConfirmDialog(onSuccess);
  });
}

/**
 * Show confirmation dialog for limit reset.
 *
 * @param {Function} onSuccess - Callback function for successful reset
 */
function showConfirmDialog(onSuccess) {
  // Create dialog overlay
  const overlay = document.createElement('div');
  overlay.className = 'confirm-dialog-overlay';
  overlay.setAttribute('role', 'dialog');
  overlay.setAttribute('aria-modal', 'true');
  overlay.setAttribute('aria-labelledby', 'confirm-dialog-title');

  // Create dialog content
  overlay.innerHTML = `
    <div class="confirm-dialog">
      <div class="confirm-dialog-header">
        <h3 id="confirm-dialog-title" class="confirm-dialog-title">
          Tilbakestill daglig grense
        </h3>
      </div>
      <div class="confirm-dialog-body">
        <p class="confirm-dialog-message">
          Er du sikker på at du vil tilbakestille dagens grense?
        </p>
        <p class="confirm-dialog-details" style="color: var(--color-charcoal-text); font-weight: 400; margin-top: var(--space-md);">
          Dette vil slette dagens visningshistorikk (unntatt manuelle og bonusvideoer).
          Barnet kan fortsette å se videoer umiddelbart.
        </p>
      </div>
      <div class="confirm-dialog-actions">
        <button
          type="button"
          class="btn btn-secondary"
          id="confirm-cancel"
        >
          Avbryt
        </button>
        <button
          type="button"
          class="btn btn-danger"
          id="confirm-reset"
        >
          Tilbakestill
        </button>
      </div>
    </div>
  `;

  // Add to DOM
  document.body.appendChild(overlay);

  // Get buttons
  const cancelButton = overlay.querySelector('#confirm-cancel');
  const confirmButton = overlay.querySelector('#confirm-reset');

  // Focus first button (Cancel)
  setTimeout(() => cancelButton.focus(), 0);

  // Cancel handler
  const handleCancel = () => {
    overlay.remove();
  };

  // Confirm handler
  const handleConfirm = async () => {
    // Disable buttons during API call
    confirmButton.disabled = true;
    cancelButton.disabled = true;
    confirmButton.setAttribute('aria-busy', 'true');

    try {
      // Call reset API endpoint
      const response = await fetch('/admin/limit/reset', {
        method: 'POST',
        credentials: 'include', // Include session cookie
      });

      if (!response.ok) {
        // Handle HTTP errors
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || 'Kunne ikke tilbakestille grense');
      }

      const data = await response.json();

      // Close dialog
      overlay.remove();

      // Call success callback with new limit data
      if (onSuccess && data.newLimit) {
        onSuccess(data.newLimit);
      }

      // Show success notification
      showSuccessNotification(data.message || 'Daglig grense tilbakestilt');
    } catch (error) {
      console.error('Error resetting limit:', error);

      // Re-enable buttons
      confirmButton.disabled = false;
      cancelButton.disabled = false;
      confirmButton.removeAttribute('aria-busy');

      // Show error message
      showErrorInDialog(overlay, error.message);
    }
  };

  // Event listeners
  cancelButton.addEventListener('click', handleCancel);
  confirmButton.addEventListener('click', handleConfirm);

  // Close on overlay click (outside dialog)
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      handleCancel();
    }
  });

  // Keyboard navigation
  overlay.addEventListener('keydown', (e) => {
    // Escape key closes dialog
    if (e.key === 'Escape') {
      handleCancel();
    }

    // Enter key confirms (if confirm button has focus)
    if (e.key === 'Enter' && document.activeElement === confirmButton) {
      handleConfirm();
    }

    // Tab key trap focus within dialog
    if (e.key === 'Tab') {
      const focusableElements = overlay.querySelectorAll(
        'button:not([disabled]), [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault();
        lastElement.focus();
      } else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault();
        firstElement.focus();
      }
    }
  });
}

/**
 * Show error message in dialog.
 *
 * @param {HTMLElement} overlay - Dialog overlay element
 * @param {string} message - Error message to display
 */
function showErrorInDialog(overlay, message) {
  const dialogBody = overlay.querySelector('.confirm-dialog-body');
  if (!dialogBody) return;

  // Remove any existing error message
  const existingError = dialogBody.querySelector('.error-message');
  if (existingError) {
    existingError.remove();
  }

  // Add error message
  const errorDiv = document.createElement('div');
  errorDiv.className = 'message-container message-error';
  errorDiv.style.marginTop = 'var(--space-md)';
  errorDiv.textContent = message;
  errorDiv.setAttribute('role', 'alert');

  dialogBody.appendChild(errorDiv);
}

/**
 * Show success notification after reset.
 *
 * @param {string} message - Success message to display
 */
function showSuccessNotification(message) {
  // Create notification
  const notification = document.createElement('div');
  notification.className = 'message-container message-success';
  notification.style.position = 'fixed';
  notification.style.top = 'var(--space-xl)';
  notification.style.right = 'var(--space-xl)';
  notification.style.zIndex = '10000';
  notification.style.minWidth = '300px';
  notification.textContent = message;
  notification.setAttribute('role', 'status');
  notification.setAttribute('aria-live', 'polite');

  // Add to DOM
  document.body.appendChild(notification);

  // Auto-remove after 3 seconds
  setTimeout(() => {
    notification.style.transition = 'opacity 0.3s ease';
    notification.style.opacity = '0';
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}
