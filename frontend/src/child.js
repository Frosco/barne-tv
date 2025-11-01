/**
 * Child interface entry point - video grid and playback
 */
import './main.css';
import { initGrid } from './child/grid.js';
import { initLimitTracker } from './child/limit-tracker.js';

console.log('Child interface initialized');

// Initialize video grid and limit tracker when DOM is loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    initGrid();
    initLimitTracker();
  });
} else {
  // DOM already loaded
  initGrid();
  initLimitTracker();
}
