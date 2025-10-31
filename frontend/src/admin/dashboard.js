/**
 * Admin Dashboard Module (Story 3.X)
 *
 * Handles:
 * - FAQ accordion initialization
 * - Dashboard functionality
 */

import { createFAQ } from '../shared/help.js';

/**
 * Initialize dashboard page.
 */
export function initDashboard() {
  initFAQ();
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

// Initialize on DOM ready (skip in test environment)
// eslint-disable-next-line no-undef
if (typeof process === 'undefined' || process.env.NODE_ENV !== 'test') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
  } else {
    initDashboard();
  }
}
