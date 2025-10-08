/**
 * Sample frontend test.
 *
 * Verifies that vitest and happy-dom are correctly configured.
 */

import { describe, it, expect, beforeEach } from 'vitest';

describe('Testing Infrastructure', () => {
  beforeEach(() => {
    document.body.innerHTML = '<div id="app"></div>';
  });

  it('verifies DOM manipulation works', () => {
    // Arrange
    const app = document.getElementById('app');

    // Act
    const heading = document.createElement('h1');
    heading.textContent = 'Hello Test';
    app.appendChild(heading);

    // Assert
    expect(app.querySelector('h1').textContent).toBe('Hello Test');
  });

  it('verifies happy-dom environment', () => {
    // Assert
    expect(document).toBeDefined();
    expect(window).toBeDefined();
    expect(document.querySelector).toBeDefined();
  });

  it('verifies element creation and attributes', () => {
    // Arrange
    const app = document.getElementById('app');

    // Act
    const button = document.createElement('button');
    button.id = 'test-button';
    button.className = 'btn btn-primary';
    button.textContent = 'Click Me';
    button.setAttribute('data-testid', 'sample-btn');
    app.appendChild(button);

    // Assert
    const foundButton = document.getElementById('test-button');
    expect(foundButton).toBeDefined();
    expect(foundButton.className).toBe('btn btn-primary');
    expect(foundButton.textContent).toBe('Click Me');
    expect(foundButton.getAttribute('data-testid')).toBe('sample-btn');
  });
});
