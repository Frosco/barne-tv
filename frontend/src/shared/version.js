/**
 * Version Display Module (Story 3.X)
 * Displays application version in footer
 */

/**
 * Display version number in footer.
 * Reads version from Vite environment variable injected at build time.
 */
export function displayVersion() {
  const version = import.meta.env.VITE_APP_VERSION || '1.0.0';
  const versionElement = document.querySelector('.version-number');

  if (versionElement) {
    versionElement.textContent = `Versjon ${version}`;
  }
}

// Initialize on DOM ready (skip in test environment)
// eslint-disable-next-line no-undef
if (typeof process === 'undefined' || process.env.NODE_ENV !== 'test') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', displayVersion);
  } else {
    displayVersion();
  }
}
