/**
 * Admin Dashboard Module (Story 3.X)
 *
 * Handles:
 * - FAQ accordion initialization
 * - Dashboard functionality
 */

import { createFAQ } from '../shared/help.js';
import { initLimitReset } from './limit-reset.js';

/**
 * Initialize dashboard page.
 */
export function initDashboard() {
  initFAQ();
  initLimitStatus();
}

/**
 * Initialize FAQ accordion (Story 3.X).
 * Creates and inserts FAQ section into dashboard.
 */
function initFAQ() {
  const faqContainer = document.getElementById('faq-container');
  if (!faqContainer) {
    return;
  }

  // Define FAQ questions and answers (Norwegian)
  const questions = [
    {
      question: 'Hvordan legger jeg til en ny YouTube-kanal?',
      answer:
        'Gå til "Kanaler"-fanen fra dashboardet. Lim inn YouTube-kanal URL (f.eks. https://www.youtube.com/@Blippi) eller kanal-ID i tekstfeltet, og klikk "Legg til kanal". Systemet henter automatisk alle videoer fra kanalen. Du kan også legge til spillelister på samme måte.',
    },
    {
      question: 'Hva er forskjellen på kanaler og spillelister?',
      answer:
        'En kanal inneholder alle videoer publisert av en bestemt YouTube-konto. Når du legger til en kanal, hentes alle dens videoer. En spilleliste er en kuratert samling av utvalgte videoer, laget av kanaleieren eller andre brukere. Begge typer kan legges til på samme måte.',
    },
    {
      question: 'Hvordan fungerer den daglige grensen?',
      answer:
        'Den daglige grensen bestemmer hvor mange minutter barnet kan se videoer hver dag. Grensen tilbakestilles automatisk ved midnatt (UTC). Når det er mindre enn 10 minutter igjen, går systemet over i "avslutningsmodus" som bare viser korte videoer. Etter at grensen er nådd, får barnet velge én "takkvideo" på maks 5 minutter.',
    },
    {
      question: 'Kan barnet se videoer etter at grensen er nådd?',
      answer:
        'Ja, etter at den daglige grensen er nådd, får barnet velge én siste video (maks 5 minutter) som kalles en "takkvideo". Denne telles ikke mot dagens eller morgendagens grense. Dette gir en myk overgang fra videovisning til andre aktiviteter. Etter takkvideoen låses systemet til neste dag.',
    },
    {
      question: 'Hva betyr "avslutningsmodus"?',
      answer:
        'Avslutningsmodus aktiveres automatisk når det er mindre enn 10 minutter igjen av den daglige grensen. I denne modusen filtreres videorutenettet til å bare vise korte videoer som passer i gjenstående tid. Dette hjelper barnet med å avslutte naturlig uten å bli avbrutt midt i en lang video.',
    },
    {
      question: 'Hvordan kan jeg spille av en spesifikk video for barnet?',
      answer:
        'Gå til "Historikk"-fanen og finn videoen du ønsker. Klikk på "Spill av igjen"-knappen ved siden av videoen. Dette lar deg forhåndsvise videoer eller vise favorittvideoer på nytt uten at det telles mot barnets daglige grense. Nyttig for gjensyn eller forhåndsvisning av innhold.',
    },
    {
      question: 'Telles foreldre-avspilling mot barnets grense?',
      answer:
        'Nei, når du som forelder bruker "Spill av igjen"-funksjonen fra historikken, telles det ikke mot barnets daglige grense. Dette kalles "manuell avspilling" og er merket i systemet. På den måten kan du forhåndsvise eller gjense innhold uten å påvirke barnets kvote.',
    },
  ];

  // Create and insert FAQ
  const faqSection = createFAQ(questions);
  faqContainer.appendChild(faqSection);
}

/**
 * Initialize daily limit status display (Story 4.1, Task 5).
 * Fetches and displays current daily limit state.
 */
async function initLimitStatus() {
  const container = document.getElementById('limit-status-container');
  if (!container) {
    return;
  }

  try {
    // Fetch limit status from API
    const response = await fetch('/api/limit/status');
    if (!response.ok) {
      throw new Error('Failed to fetch limit status');
    }

    const limitData = await response.json();

    // Render limit status display
    renderLimitStatus(container, limitData);
  } catch (error) {
    console.error('Error fetching limit status:', error);
    renderLimitError(container);
  }
}

/**
 * Render limit status display with cards and badge.
 *
 * @param {HTMLElement} container - Container element
 * @param {Object} limitData - Limit status data from API
 */
function renderLimitStatus(container, limitData) {
  const { minutesWatched, minutesRemaining, currentState, resetTime } =
    limitData;

  // Convert reset time to local time for display
  const resetDate = new Date(resetTime);
  const localResetTime = resetDate.toLocaleTimeString('no-NO', {
    hour: '2-digit',
    minute: '2-digit',
  });

  // State badge configuration
  const stateConfig = {
    normal: { label: 'Normal', icon: '✅', class: 'normal' },
    winddown: { label: 'Avslutter snart', icon: '⏳', class: 'winddown' },
    grace: { label: 'Bonusvideo tilgjengelig', icon: '🎁', class: 'grace' },
    locked: { label: 'Låst til midnatt', icon: '🔒', class: 'locked' },
  };

  const state = stateConfig[currentState] || stateConfig.normal;

  // Build HTML
  container.innerHTML = `
    <div class="limit-status__card">
      <span class="limit-status__label">Minutter sett</span>
      <div class="limit-status__value">
        ${minutesWatched}
        <span class="limit-status__unit">min</span>
      </div>
    </div>

    <div class="limit-status__card">
      <span class="limit-status__label">Minutter igjen</span>
      <div class="limit-status__value">
        ${minutesRemaining}
        <span class="limit-status__unit">min</span>
      </div>
    </div>

    <div class="limit-status__badge-container">
      <div style="display: flex; align-items: center; gap: var(--space-lg); flex-wrap: wrap;">
        <div
          class="limit-status__badge limit-status__badge--${state.class}"
          role="status"
          aria-label="Daglig grense status: ${state.label}"
        >
          <span class="limit-status__badge-icon">${state.icon}</span>
          <span>${state.label}</span>
        </div>

        <span class="limit-status__reset-time">
          🕐 Tilbakestilles ${localResetTime}
        </span>
      </div>

      <button
        class="limit-status__reset-button"
        id="reset-limit-button"
        aria-label="Tilbakestill daglig grense"
      >
        🔄 Tilbakestill grense
      </button>
    </div>
  `;

  // Initialize reset button functionality (Task 6)
  // Create callback that re-renders and re-initializes on success
  const handleResetSuccess = (newLimitData) => {
    renderLimitStatus(container, newLimitData);
  };

  initLimitReset(handleResetSuccess);
}

/**
 * Render error state for limit status.
 *
 * @param {HTMLElement} container - Container element
 */
function renderLimitError(container) {
  container.innerHTML = `
    <div class="limit-status__error">
      ⚠️ Kunne ikke laste daglig grensestatus. Prøv å oppdatere siden.
    </div>
  `;
}

// Initialize on DOM ready (skip in test environment)
// eslint-disable-next-line no-undef
if (typeof process === 'undefined' || process.env.NODE_ENV !== 'test') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
  } else {
    initDashboard();
  }
}
