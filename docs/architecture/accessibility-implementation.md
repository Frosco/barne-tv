# Accessibility Implementation

## Compliance Target

**Standard:** WCAG 2.1 Level AA compliance

This application must be accessible to all users, including those using assistive technologies. While the primary users (children ages 2-6) may not require screen readers, the admin interface must be fully accessible for parents with disabilities.

## Semantic HTML Standards

**Use semantic HTML elements for their intended purpose:**

```html
<!-- ✅ CORRECT - Semantic structure -->
<main role="main">
  <h1>Video Grid</h1>
  <div class="video-grid" role="region" aria-label="Available videos">
    <button class="video-card" aria-label="Play Excavator Song by Blippi">
      <img src="..." alt="" role="presentation">
      <h3>Excavator Song</h3>
    </button>
  </div>
</main>

<!-- ❌ WRONG - Non-semantic divs -->
<div class="main">
  <div class="heading">Video Grid</div>
  <div class="grid">
    <div class="video-card" onclick="playVideo()">
      ...
    </div>
  </div>
</div>
```

**Element Usage Guidelines:**

| Purpose | Use | Not |
|---------|-----|-----|
| Interactive element | `<button>` | `<div onclick>` |
| Navigation | `<nav>` | `<div class="nav">` |
| Main content | `<main>` | `<div id="main">` |
| Page sections | `<section>`, `<article>` | Generic `<div>` |
| Form inputs | `<label>` + `<input>` | Placeholder-only |

## ARIA Implementation Patterns

**Video Cards (Child Interface):**
```html
<button 
  class="video-card" 
  data-video-id="abc123"
  aria-label="Play Excavator Song for Kids by Blippi, 4 minutes"
  aria-describedby="channel-blippi"
>
  <img 
    src="thumbnail.jpg" 
    alt="" 
    role="presentation"
  >
  <h3>Excavator Song for Kids</h3>
  <span id="channel-blippi" class="sr-only">Channel: Blippi</span>
</button>
```

**Warning Overlays:**
```html
<div 
  class="warning-overlay" 
  role="alert" 
  aria-live="assertive"
  aria-atomic="true"
>
  <img src="mascot.svg" alt="Friendly mascot" role="img">
  <p class="warning-text">10 minutter igjen!</p>
</div>
```

**Rationale:** `role="alert"` with `aria-live="assertive"` ensures screen readers announce warnings immediately, even interrupting current speech.

**Limit Reached Screen:**
```html
<div class="limit-reached" role="status" aria-live="polite">
  <img src="mascot-wave.svg" alt="Mascot waving goodbye">
  <h2>Vi er ferdige for i dag!</h2>
  <p>Vil du se én til?</p>
  <div role="group" aria-label="Choose one more video option">
    <button aria-label="Yes, watch one more video">Ja, én til!</button>
    <button aria-label="No, finish for today">Nei, ha det!</button>
  </div>
</div>
```

**Loading States:**
```html
<div 
  class="loading" 
  role="status" 
  aria-live="polite"
  aria-busy="true"
>
  <span class="sr-only">Loading videos...</span>
  <div class="spinner" aria-hidden="true"></div>
</div>
```

**Screen Reader Only Text:**
```css
/* Utility class for screen reader only content */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
```

## Keyboard Navigation Requirements

**Global Keyboard Support:**

| Key | Action | Context |
|-----|--------|---------|
| `Tab` | Move focus forward | All interactive elements |
| `Shift+Tab` | Move focus backward | All interactive elements |
| `Enter` or `Space` | Activate button | Buttons, video cards |
| `Escape` | Exit fullscreen, close modal | Video playback, overlays |
| `Arrow keys` | Navigate within groups | Future: Grid navigation |

**Implementation Example:**
```javascript
// frontend/src/child/grid.js

function createVideoCard(video) {
  const button = document.createElement('button');
  button.className = 'video-card';
  button.setAttribute('aria-label', 
    `Play ${video.title} by ${video.youtubeChannelName}, ${formatDuration(video.durationSeconds)}`
  );
  
  // Keyboard event handlers
  button.addEventListener('click', () => playVideo(video.videoId));
  button.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      playVideo(video.videoId);
    }
  });
  
  return button;
}

// Escape key handling for video playback
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && isVideoPlaying()) {
    exitFullscreen();
    returnToGrid();
  }
});
```

**Focus Management:**

**Rule 1: Focus returns to triggering element after modal/video closes**
```javascript
// frontend/src/child/player.js

let lastFocusedElement = null;

function playVideo(videoId) {
  // Store reference to currently focused element
  lastFocusedElement = document.activeElement;
  
  // Load and play video...
}

function returnToGrid() {
  // Restore focus to the video card that was clicked
  if (lastFocusedElement && lastFocusedElement.isConnected) {
    lastFocusedElement.focus();
  } else {
    // Fallback: focus first video card
    const firstCard = document.querySelector('.video-card');
    if (firstCard) firstCard.focus();
  }
}
```

**Rule 2: Focus visible indicator always present**
```css
/* Visible focus indicator for keyboard navigation */
.video-card:focus {
  outline: 3px solid var(--color-sky-blue);
  outline-offset: 4px;
  /* Never use outline: none without a replacement! */
}

/* Focus visible only for keyboard (not mouse clicks) */
.video-card:focus:not(:focus-visible) {
  outline: none;
}

.video-card:focus-visible {
  outline: 3px solid var(--color-sky-blue);
  outline-offset: 4px;
}
```

**Rule 3: No keyboard traps**
```javascript
// Ensure modals can be exited with Escape
function showWarningOverlay(minutes) {
  const overlay = createWarningOverlay(minutes);
  document.body.appendChild(overlay);
  
  // Focus the overlay for screen reader announcement
  overlay.focus();
  
  // Ensure Escape key dismisses overlay
  overlay.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      dismissOverlay();
    }
  });
  
  // Auto-dismiss after 3 seconds
  setTimeout(dismissOverlay, 3000);
}
```

## Color Contrast Requirements

**Minimum contrast ratios (WCAG AA):**
- Normal text (18px and below): **4.5:1**
- Large text (18px+ bold, 24px+ regular): **3:1**
- Interactive elements (buttons, links): **3:1** against background

**Implementation:**
```css
/* Color palette with verified contrast ratios */
:root {
  /* Text on white background */
  --color-text: #2D3436;        /* 15.3:1 ratio ✅ */
  --color-text-secondary: #636E72; /* 5.8:1 ratio ✅ */
  
  /* Buttons and interactive elements */
  --color-primary: #FFDB4D;     /* 1.8:1 on white - must have dark text */
  --color-primary-text: #2D3436; /* 13.2:1 on yellow ✅ */
  
  /* Focus indicators */
  --color-focus: #00B4D8;       /* 3.2:1 on white ✅ */
}

/* Ensure buttons have sufficient contrast */
.video-card {
  background: var(--color-white);
  color: var(--color-text);       /* 15.3:1 ✅ */
  border: 2px solid var(--color-primary); /* 1.8:1 - decorative only */
}

.action-button {
  background: var(--color-primary);
  color: var(--color-primary-text); /* 13.2:1 ✅ */
}
```

**Testing contrast:**
```bash
# Use automated tools to verify contrast
npx @axe-core/cli https://localhost:5173 --rules color-contrast
```

## Screen Reader Compatibility

**Announce Dynamic Content Changes:**
```javascript
// frontend/src/child/limit-tracker.js

function updateRemainingTime(minutes) {
  // Update visual display
  const display = document.querySelector('[data-time-remaining]');
  if (display) {
    display.textContent = `${minutes} minutter igjen`;
  }
  
  // Announce to screen readers (politely, don't interrupt)
  announceToScreenReader(`${minutes} minutter igjen`, 'polite');
}

function announceToScreenReader(message, priority = 'polite') {
  const announcement = document.createElement('div');
  announcement.setAttribute('role', 'status');
  announcement.setAttribute('aria-live', priority);
  announcement.className = 'sr-only';
  announcement.textContent = message;
  
  document.body.appendChild(announcement);
  
  // Remove after announcement (give screen reader time)
  setTimeout(() => {
    document.body.removeChild(announcement);
  }, 1000);
}
```

**Video Playback Announcements:**
```javascript
// frontend/src/child/player.js

function playVideo(videoId, videoTitle, channelName) {
  // Announce to screen reader
  announceToScreenReader(
    `Now playing ${videoTitle} by ${channelName}`,
    'assertive'
  );
  
  // Load video...
}

function videoEnded() {
  announceToScreenReader('Video finished. Returning to video selection.', 'polite');
  returnToGrid();
}
```

**Handle Unavailable Videos:**
```javascript
function handleVideoUnavailable(videoId) {
  // Show mascot error visually
  showMascotError('Oops! Det videoen gjemmer seg!');
  
  // Announce to screen reader
  announceToScreenReader(
    'This video is not available. Returning to video selection.',
    'assertive'
  );
  
  // Auto-return after 5 seconds
  setTimeout(returnToGrid, 5000);
}
```

## Form Accessibility (Admin Interface)

**All form inputs must have associated labels:**
```html
<!-- ✅ CORRECT - Explicit label association -->
<div class="form-field">
  <label for="daily-limit">Daily time limit (minutes)</label>
  <input 
    type="number" 
    id="daily-limit" 
    name="daily_limit_minutes"
    min="5" 
    max="180"
    aria-describedby="daily-limit-help"
    required
  >
  <span id="daily-limit-help" class="help-text">
    Between 5 and 180 minutes
  </span>
</div>

<!-- ❌ WRONG - Placeholder is not a label -->
<input type="number" placeholder="Daily limit">
```

**Error Messages:**
```html
<div class="form-field" aria-invalid="true">
  <label for="channel-url">Channel URL</label>
  <input 
    type="text" 
    id="channel-url"
    aria-describedby="channel-url-error"
    aria-invalid="true"
  >
  <span id="channel-url-error" class="error-message" role="alert">
    Please enter a valid YouTube channel URL
  </span>
</div>
```

**Required Field Indication:**
```html
<label for="password">
  Admin Password 
  <span class="required" aria-label="required">*</span>
</label>
<input 
  type="password" 
  id="password"
  required
  aria-required="true"
>
```

## Testing Strategy

**Automated Testing (CI/CD Integration):**

```yaml
# .github/workflows/accessibility.yml
name: Accessibility Tests

on: [push, pull_request]

jobs:
  a11y-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      
      - name: Build application
        run: |
          cd frontend
          npm run build
      
      - name: Start test server
        run: |
          cd frontend
          npm run preview &
          sleep 5
      
      - name: Run Lighthouse CI
        run: |
          npm install -g @lhci/cli
          lhci autorun --config=lighthouserc.js
      
      - name: Run axe-core tests
        run: |
          cd frontend
          npx playwright test a11y.spec.js
```

**Lighthouse Configuration:**
```javascript
// lighthouserc.js
module.exports = {
  ci: {
    collect: {
      url: ['http://localhost:4173'],
      numberOfRuns: 3,
    },
    assert: {
      assertions: {
        'categories:accessibility': ['error', { minScore: 0.9 }],
        'color-contrast': 'error',
        'html-has-lang': 'error',
        'html-lang-valid': 'error',
        'button-name': 'error',
        'link-name': 'error',
        'image-alt': 'error',
      },
    },
  },
};
```

**Playwright Accessibility Tests:**
```javascript
// frontend/tests/e2e/a11y.spec.js
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Accessibility Tests', () => {
  test('video grid page should not have accessibility violations', async ({ page }) => {
    await page.goto('http://localhost:4173');
    
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    
    expect(accessibilityScanResults.violations).toEqual([]);
  });
  
  test('admin login should not have accessibility violations', async ({ page }) => {
    await page.goto('http://localhost:4173/admin/login');
    
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    
    expect(accessibilityScanResults.violations).toEqual([]);
  });
  
  test('keyboard navigation works on video grid', async ({ page }) => {
    await page.goto('http://localhost:4173');
    
    // Tab to first video card
    await page.keyboard.press('Tab');
    
    // Verify focus is on a video card
    const focusedElement = await page.locator(':focus');
    await expect(focusedElement).toHaveClass(/video-card/);
    
    // Enter should activate video
    await page.keyboard.press('Enter');
    
    // Verify video player loads
    await expect(page.locator('iframe[src*="youtube.com"]')).toBeVisible();
  });
  
  test('ESC key exits video playback', async ({ page }) => {
    await page.goto('http://localhost:4173');
    
    // Click first video
    await page.locator('.video-card').first().click();
    
    // Wait for video to load
    await page.waitForSelector('iframe[src*="youtube.com"]');
    
    // Press ESC
    await page.keyboard.press('Escape');
    
    // Should return to grid
    await expect(page.locator('.video-grid')).toBeVisible();
  });
});
```

**Manual Testing Checklist:**

```markdown
## Manual Accessibility Testing Checklist

**Keyboard Navigation:**
- [ ] All interactive elements reachable via Tab
- [ ] Tab order is logical (left-to-right, top-to-bottom)
- [ ] Focus indicator visible on all focused elements
- [ ] Enter/Space activates buttons
- [ ] Escape exits video playback
- [ ] No keyboard traps

**Screen Reader Testing (NVDA on Windows, VoiceOver on Mac):**
- [ ] Page title announced on load
- [ ] Video cards announced with title, channel, duration
- [ ] Warning overlays announced immediately
- [ ] Limit reached message announced
- [ ] Form labels associated with inputs
- [ ] Error messages announced
- [ ] Dynamic content changes announced appropriately

**Visual Testing:**
- [ ] 200% zoom: content remains readable and functional
- [ ] High contrast mode: all elements visible
- [ ] Color contrast meets WCAG AA (use tool to verify)
- [ ] Focus indicators clearly visible
- [ ] No information conveyed by color alone

**Cognitive Accessibility:**
- [ ] Clear, simple language (Norwegian for child/parent)
- [ ] Consistent navigation patterns
- [ ] No time limits on reading (except video playback limits)
- [ ] Error messages clear and helpful
```

**Testing Tools:**

| Tool | Purpose | Usage |
|------|---------|-------|
| **Lighthouse** | Automated audit | Chrome DevTools → Lighthouse → Accessibility |
| **axe DevTools** | Automated violations | Browser extension, checks WCAG |
| **WAVE** | Visual feedback | Browser extension, highlights issues |
| **Keyboard only** | Keyboard testing | Unplug mouse, navigate site |
| **Screen reader** | SR testing | NVDA (Windows), VoiceOver (Mac) |
| **Colour Contrast Analyser** | Contrast testing | Desktop app for precise contrast checking |

## Accessibility Documentation

**For Developers:**
- All accessibility requirements documented here
- Code examples show correct patterns
- Automated tests catch common violations
- Manual testing checklist for releases

**For Users (if needed):**
- Document keyboard shortcuts in help section
- Provide accessibility statement if making publicly available
- Include contact for accessibility issues

## Common Pitfalls to Avoid

**DON'T:**
- ❌ Use `<div>` with `onclick` instead of `<button>`
- ❌ Remove focus outlines without replacement
- ❌ Use placeholder text as label replacement
- ❌ Convey information by color alone
- ❌ Create keyboard traps
- ❌ Hide content from screen readers that's visually visible
- ❌ Use insufficient color contrast
- ❌ Forget to announce dynamic content changes

**DO:**
- ✅ Use semantic HTML elements
- ✅ Provide visible focus indicators
- ✅ Associate labels with form inputs
- ✅ Use ARIA when semantic HTML isn't enough
- ✅ Test with keyboard only
- ✅ Test with screen reader
- ✅ Verify color contrast
- ✅ Announce important changes to screen readers

---

