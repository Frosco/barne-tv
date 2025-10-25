/**
 * Child interface entry point - video grid and playback
 */
import './main.css';
import { initGrid } from './child/grid.js';

console.log('Child interface initialized');

// Initialize video grid when DOM is loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initGrid);
} else {
  // DOM already loaded
  initGrid();
}
