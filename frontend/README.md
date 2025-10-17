# Frontend Development Documentation

This document provides comprehensive guidance for developing the Safe YouTube Viewer for Kids frontend application.

## Quick Start

```bash
# Install dependencies
npm install

# Start development server (http://localhost:5173)
npm run dev

# Run tests
npm test

# Run tests with coverage
npm run test:coverage

# Lint code
npm run lint

# Auto-fix linting issues
npm run lint:fix

# Build for production
npm run build

# Preview production build
npm run preview
```

## Directory Structure

```
frontend/
├── src/                      # Source files
│   ├── child/               # Child interface modules (future)
│   ├── admin/               # Admin interface modules (future)
│   ├── shared/              # Shared utilities (future)
│   ├── child.js             # Child interface entry point
│   ├── admin.js             # Admin interface entry point
│   ├── main.css             # Global styles with design system
│   └── sample.test.js       # Test infrastructure verification
├── public/                   # Static assets (served as-is)
│   ├── images/              # Images and icons
│   │   └── mascot/          # Mascot SVG files (future)
│   └── sounds/              # Audio files (future)
├── templates/                # Jinja2 server-rendered templates
│   ├── base.html            # Base template with Vite integration
│   ├── child/               # Child interface templates (future)
│   └── admin/               # Admin interface templates (future)
├── vite.config.js           # Vite build configuration
├── vitest.config.js         # Vitest test configuration
├── eslint.config.js         # ESLint linting configuration (flat config)
├── .prettierrc              # Prettier formatting configuration
├── package.json             # Dependencies and scripts
└── README.md                # This file
```

### Key Directory Notes

- **src/**: Contains all JavaScript source code and CSS
  - Tests are collocated with source files (vitest convention)
  - Entry points (child.js, admin.js) create separate bundles

- **public/**: Static assets copied to build output as-is
  - Images, sounds, fonts
  - No processing or optimization

- **templates/**: Jinja2 templates served by FastAPI backend
  - Templates load appropriate JavaScript bundles
  - Server-side rendering with progressive enhancement

- **static/**: (Generated, in .gitignore) Build output directory
  - Created by `npm run build`
  - Contains hashed asset files for cache-busting
  - Served by Nginx in production

## Development Workflow

### 1. Development Mode

Start the Vite dev server for hot module replacement (HMR):

```bash
npm run dev
```

- Server runs at **http://localhost:5173**
- Changes to JavaScript/CSS instantly update in browser
- API requests to `/api/*` proxied to `http://localhost:8000` (FastAPI backend)

**Note:** You'll see a 404 when accessing http://localhost:5173 directly. This is expected - HTML pages are served by the FastAPI backend using Jinja2 templates, not by Vite.

### 2. Backend Integration

The backend serves Jinja2 templates that load Vite assets:

**Development:**
- Templates load source files from Vite dev server
- Example: `http://localhost:5173/src/child.js`

**Production:**
- Templates load pre-built bundles from static/
- Example: `/static/assets/child-[hash].js`

### 3. Building for Production

Build optimized production assets:

```bash
npm run build
```

**Output:**
- Creates `static/` directory (sibling to frontend/)
- Bundles JavaScript with code splitting
- Extracts and minifies CSS
- Adds content hashes for cache-busting
- Example: `static/assets/child-CMgO8nVg.js`

### 4. Testing

Run unit tests with Vitest:

```bash
npm test           # Run tests in watch mode
npm run test:coverage  # Generate coverage report
```

Tests use happy-dom for lightweight DOM simulation.

### 5. Code Quality

Lint and format code:

```bash
npm run lint       # Check for linting errors
npm run lint:fix   # Auto-fix linting issues
```

**ESLint:** Enforces code quality rules (ES2021, browser environment)
**Prettier:** Ensures consistent code formatting

## Vite Configuration

**File:** `vite.config.js`

### Dual Entry Points

Two separate JavaScript bundles for different interfaces:

```javascript
input: {
  child: './src/child.js',   // Child interface (video grid, playback)
  admin: './src/admin.js'    // Admin interface (management, settings)
}
```

**Why separate bundles?**
- Child and admin never run simultaneously
- Reduces bundle size for each interface
- Improves load performance

### Build Output

```javascript
outDir: '../static'       // Build to project root static/
emptyOutDir: true         // Clean before each build
```

### Development Server

```javascript
server: {
  proxy: {
    '/api': 'http://localhost:8000'  // Proxy API calls to FastAPI
  }
}
```

### Public Assets

```javascript
publicDir: 'public'  // Static assets copied to build output
```

## CSS Design System

**File:** `src/main.css`

### Color Palette (14 Colors)

```css
/* Primary Colors */
--color-primary-yellow: #FFDB4D;
--color-soft-white: #FEFEFE;
--color-charcoal-text: #2D3436;

/* Rainbow Supporting Colors */
--color-coral: #FF6B6B;
--color-sky-blue: #00B4D8;
--color-soft-purple: #A8DADC;
--color-mint-green: #06D6A0;
--color-orange: #FF9500;
--color-lavender: #B8B8D1;

/* Functional Colors */
--color-success: #06D6A0;
--color-warning: #FFB830;
--color-error: #E63946;
--color-neutral-gray: #95A5A6;
--color-light-gray: #F1F3F5;
```

### Spacing Scale (8px base)

```css
--space-xs: 4px;
--space-sm: 8px;
--space-md: 16px;
--space-lg: 24px;
--space-xl: 32px;
--space-2xl: 40px;
--space-3xl: 48px;
```

### Typography Scale

```css
--font-size-h1: 48px;
--font-size-h2: 36px;
--font-size-h3: 32px;
--font-size-large-body: 24px;
--font-size-body: 18px;
--font-size-small-body: 16px;
--font-size-caption: 14px;

--font-family-primary: 'Inter', -apple-system, ...;
```

### Design Tokens

**Shadows:** `--shadow-sm`, `--shadow-md`, `--shadow-lg`, `--shadow-xl`
**Radius:** `--radius-sm` (6px), `--radius-md` (8px), `--radius-lg` (12px), `--radius-xl` (16px), `--radius-full` (9999px)
**Breakpoints:** `--breakpoint-tablet` (768px), `--breakpoint-desktop` (1024px)

### Placeholder Components

```css
.video-card         /* Video thumbnail cards */
.action-button      /* Large touch-friendly buttons */
.warning-overlay    /* Full-screen overlays */
.sr-only            /* Screen reader only content */
```

## Utility Classes

**File:** `src/main.css`

Utility classes provide quick, single-purpose styling for common typography and spacing needs. Use them directly in HTML to avoid writing custom CSS.

### Typography Utilities

Apply consistent text styling using the design system's typography scale:

| Class | Font Size | Weight | Line Height | Usage |
|-------|-----------|--------|-------------|-------|
| `.h1` | 48px | 700 Bold | 1.2 | Large headings, goodbye messages |
| `.h2` | 36px | 700 Bold | 1.3 | Section headings, limit screen |
| `.h3` | 32px | 700 Bold | 1.3 | Subsection headings, warnings |
| `.large-body` | 24px | 600 Semi-bold | 1.4 | Button text, questions, emphasis |
| `.body-text` | 18px | 400 Regular | 1.5 | Video titles, body text |
| `.small-body` | 16px | 400 Regular | 1.5 | Channel names, secondary text |
| `.caption` | 14px | 400 Regular | 1.4 | Timestamps, metadata |

**Examples:**
```html
<h1 class="h1">Ha det! Vi ses i morgen!</h1>
<h2 class="h2">Vi er ferdige for i dag!</h2>
<p class="large-body">Vil du se én til?</p>
<p class="body-text">Video Title Here</p>
<span class="caption">2 minutes ago</span>
```

### Spacing Utilities

Apply consistent margin and padding using the 8px base scale:

**Size Scale:**
| Token | Size | Usage |
|-------|------|-------|
| `xs` | 4px | Tight spacing between related elements |
| `sm` | 8px | Standard spacing between related elements |
| `md` | 16px | Form fields, moderate spacing |
| `lg` | 24px | Grid gaps (tablet), section spacing |
| `xl` | 32px | Section separation, large spacing |
| `2xl` | 40px | Page padding (desktop), major sections |
| `3xl` | 48px | Large breathing room, max spacing |

**Naming Convention:**
- **Margin:** `.m{direction}-{size}` (e.g., `.mt-lg`, `.mx-md`, `.m-xl`)
- **Padding:** `.p{direction}-{size}` (e.g., `.pt-sm`, `.px-lg`, `.p-2xl`)

**Direction Abbreviations:**
- `t` = top
- `r` = right
- `b` = bottom
- `l` = left
- `x` = left + right (horizontal)
- `y` = top + bottom (vertical)
- (no direction) = all sides

**Available Utilities (98 total):**
```css
/* Margin: mt, mr, mb, ml, mx, my, m */
.mt-xs, .mt-sm, .mt-md, .mt-lg, .mt-xl, .mt-2xl, .mt-3xl
.mr-xs, .mr-sm, .mr-md, .mr-lg, .mr-xl, .mr-2xl, .mr-3xl
.mb-xs, .mb-sm, .mb-md, .mb-lg, .mb-xl, .mb-2xl, .mb-3xl
.ml-xs, .ml-sm, .ml-md, .ml-lg, .ml-xl, .ml-2xl, .ml-3xl
.mx-xs, .mx-sm, .mx-md, .mx-lg, .mx-xl, .mx-2xl, .mx-3xl
.my-xs, .my-sm, .my-md, .my-lg, .my-xl, .my-2xl, .my-3xl
.m-xs, .m-sm, .m-md, .m-lg, .m-xl, .m-2xl, .m-3xl

/* Padding: pt, pr, pb, pl, px, py, p */
.pt-xs, .pt-sm, .pt-md, .pt-lg, .pt-xl, .pt-2xl, .pt-3xl
.pr-xs, .pr-sm, .pr-md, .pr-lg, .pr-xl, .pr-2xl, .pr-3xl
.pb-xs, .pb-sm, .pb-md, .pb-lg, .pb-xl, .pb-2xl, .pb-3xl
.pl-xs, .pl-sm, .pl-md, .pl-lg, .pl-xl, .pl-2xl, .pl-3xl
.px-xs, .px-sm, .px-md, .px-lg, .px-xl, .px-2xl, .px-3xl
.py-xs, .py-sm, .py-md, .py-lg, .py-xl, .py-2xl, .py-3xl
.p-xs, .p-sm, .p-md, .p-lg, .p-xl, .p-2xl, .p-3xl
```

**Examples:**
```html
<!-- Typography with spacing -->
<h1 class="h1 mt-2xl mb-lg">Main Title</h1>
<h2 class="h2 mt-xl mb-md">Section Heading</h2>
<p class="body-text mb-md">Paragraph with bottom margin</p>

<!-- Card with padding and margin -->
<div class="video-card p-md mb-lg">
  <img src="thumbnail.jpg" alt="">
  <h3 class="body-text mt-sm">Video Title</h3>
</div>

<!-- Button with horizontal padding -->
<button class="action-button px-xl py-md">
  <span class="large-body">Click Me</span>
</button>

<!-- Container with all-sides padding -->
<div class="p-2xl">
  <p class="body-text">Content with padding on all sides</p>
</div>
```

### When to Use Utility Classes vs. Component Classes

**Use Utility Classes When:**
- Making quick spacing adjustments: `<div class="mb-lg">`
- Applying typography styles in templates: `<h1 class="h1">`
- Prototyping or one-off layouts: `<div class="p-md mt-xl">`
- Adding spacing between elements without custom CSS

**Use Component Classes When:**
- Building complex multi-property styles: `.video-card`
- Creating reusable components with multiple states: `.action-button`
- Implementing interactive elements with hover/active states: `.warning-overlay`
- Ensuring consistent patterns across the application

**Best Practice: Combine Both:**
```html
<!-- Component class for core styling + utilities for spacing -->
<div class="video-card mb-lg">
  <h3 class="body-text mt-sm">Video Title</h3>
</div>

<!-- Component button + utility spacing -->
<button class="action-button mt-xl px-2xl">
  <span class="large-body">Play Video</span>
</button>
```

## Template Inheritance Pattern

**File:** `templates/base.html`

### Jinja2 Template Structure

```jinja2
{% extends "base.html" %}

{% block title %}Video Grid{% endblock %}

{% block content %}
  <div class="video-grid">
    <!-- Page-specific content -->
  </div>
{% endblock %}
```

### Vite Integration

Base template loads appropriate entry point:

**Development:**
```html
<script type="module" src="http://localhost:5173/src/child.js"></script>
```

**Production:**
```html
<script type="module" src="/static/assets/child-[hash].js"></script>
```

The `interface` variable (set by backend) determines which bundle loads:
- `interface='child'` → child.js
- `interface='admin'` → admin.js

## Entry Point Strategy

### Child Interface (`src/child.js`)

```javascript
/**
 * Child interface entry point - video grid and playback
 */
import './main.css';

console.log('Child interface initialized');
```

- Imports main CSS (includes design system)
- Future: Import child-specific modules
- Minimal initial implementation (foundation only)

### Admin Interface (`src/admin.js`)

```javascript
/**
 * Admin interface entry point - channel management and settings
 */
import './main.css';

console.log('Admin interface initialized');
```

- Shares same CSS as child interface
- Future: Import admin-specific modules
- Separate bundle for performance

## Responsive Design

### Breakpoints

- **Mobile:** 320px - 767px (tertiary, admin only)
- **Tablet Portrait:** 768px - 1023px (secondary)
- **Tablet Landscape:** 1024px - 1365px (secondary)
- **Desktop:** 1366px+ (primary)

### Touch Optimization

CSS automatically adapts for touch devices:

```css
@media (hover: none) and (pointer: coarse) {
  .video-card:hover {
    transform: none;  /* Disable hover effects */
  }

  .video-card:active {
    transform: scale(0.98);  /* Touch feedback */
  }
}
```

## Accessibility

### Key Features

- **High contrast:** All text meets WCAG 2.1 AA standards
- **Focus indicators:** Visible 3px outlines on all interactive elements
- **Screen reader support:** Semantic HTML throughout
- **Reduced motion:** Respects `prefers-reduced-motion` preference
- **Keyboard navigation:** All features accessible via keyboard

### Utility Classes

```css
.sr-only  /* Visually hidden but available to screen readers */
```

## Performance Considerations

### Optimization Strategies

1. **Code splitting:** Separate child/admin bundles
2. **CSS extraction:** Single optimized CSS file
3. **Asset hashing:** Cache-busting via content hashes
4. **Tree shaking:** Unused code removed automatically
5. **Minification:** JavaScript and CSS compressed

### Build Output

```
static/
├── assets/
│   ├── child-[hash].js      (~0.07 kB)
│   ├── admin-[hash].js      (~0.07 kB)
│   └── main-[hash].css      (~3.31 kB gzipped: 1.28 kB)
└── images/                   (copied from public/)
```

## Technology Stack

- **Build Tool:** Vite 7.1.9 (zero-config, instant start, HMR)
- **Language:** Vanilla JavaScript ES2020+ (no TypeScript)
- **CSS:** Pure CSS3 with custom properties
- **Templates:** Jinja2 3.1.6 (server-side rendering)
- **Testing:** Vitest 3.2.4 + happy-dom 19.0.2
- **Linting:** ESLint 9.37.0 (flat config)
- **Formatting:** Prettier 3.1.1

## Common Tasks

### Adding a New JavaScript Module

1. Create file in appropriate directory (child/, admin/, shared/)
2. Export functions/classes
3. Import in entry point (child.js or admin.js)

### Adding Static Assets

1. Place files in `public/` directory
2. Reference in HTML: `/images/logo.svg`
3. Files copied to `static/` during build

### Adding a New Component Style

1. Add CSS class to `src/main.css`
2. Use design system tokens (colors, spacing, etc.)
3. Follow BEM-like naming convention

### Updating Dependencies

```bash
npm install <package>@<version>    # Add dependency
npm update                          # Update all dependencies
npm audit fix                       # Fix security vulnerabilities
```

## Troubleshooting

### Dev Server Won't Start

```bash
# Check if port 5173 is already in use
lsof -i :5173

# Kill process if needed
kill -9 <PID>

# Restart dev server
npm run dev
```

### Build Fails

```bash
# Clean node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Try build again
npm run build
```

### Linting Errors

```bash
# Auto-fix most issues
npm run lint:fix

# Check remaining issues
npm run lint
```

### CSS Not Loading

- Check that `import './main.css'` exists in entry point
- Verify Vite dev server is running
- Clear browser cache

## Project Links

- **Main README:** `../README.md`
- **Frontend Spec:** `../docs/front-end-spec.md`
- **Architecture Docs:** `../docs/architecture/`
- **Tech Stack:** `../docs/architecture/tech-stack.md`
- **Coding Standards:** `../docs/architecture/coding-standards.md`

## Future Development

### Upcoming Features

- Child interface modules (grid.js, player.js, limit-tracker.js)
- Admin interface modules (channels.js, history.js, settings.js)
- Shared utilities (api.js, state.js)
- Component tests for UI modules
- E2E tests with Playwright
- Mascot character images

### Testing Infrastructure

Already configured:
- ✅ Vitest for unit tests
- ✅ happy-dom for DOM simulation
- ✅ Playwright for E2E tests (future)
- ✅ Coverage reporting

### Design System Expansion

Currently implemented:
- ✅ 14-color palette
- ✅ Spacing scale (8px base)
- ✅ Typography scale
- ✅ Shadow scale
- ✅ Border radius scale
- ✅ Responsive breakpoints
- ✅ Placeholder components

Ready for component development!

---

**Version:** 1.0
**Last Updated:** 2025-10-09
**Story:** 1.Y - Frontend Foundation & Build Setup
