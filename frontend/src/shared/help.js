/**
 * Help Component Module
 * Provides tooltip and FAQ accordion components for admin interface
 * Story 3.X: Admin Help & Documentation
 */

/**
 * Create a tooltip component with keyboard accessibility
 * @param {string} triggerText - Text to display on the trigger button (e.g., "ℹ️")
 * @param {string} tooltipContent - Norwegian help text content
 * @param {string} tooltipId - Unique ID for the tooltip element
 * @returns {HTMLElement} Container with trigger button and tooltip
 */
export function createTooltip(triggerText, tooltipContent, tooltipId) {
  // Create container
  const container = document.createElement('span');
  container.className = 'tooltip-container';

  // Create trigger button
  const trigger = document.createElement('button');
  trigger.type = 'button';
  trigger.className = 'tooltip-trigger';
  trigger.textContent = triggerText;
  trigger.setAttribute('aria-describedby', tooltipId);
  trigger.setAttribute('aria-expanded', 'false');
  trigger.setAttribute('aria-label', 'Vis hjelpetekst');

  // Create tooltip element
  const tooltip = document.createElement('div');
  tooltip.id = tooltipId;
  tooltip.role = 'tooltip';
  tooltip.className = 'tooltip-content';
  tooltip.textContent = tooltipContent;
  tooltip.hidden = true;

  // Toggle tooltip visibility on click
  trigger.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();

    // Check current state BEFORE closing others
    const isHidden = tooltip.hidden;

    // Close other open tooltips first (excluding this one)
    closeAllTooltips();

    // Toggle this tooltip
    tooltip.hidden = !isHidden;
    // aria-expanded should match the NEW visible state (opposite of hidden)
    trigger.setAttribute('aria-expanded', (!tooltip.hidden).toString());

    // Focus trigger for screen reader feedback
    if (!isHidden) {
      trigger.focus();
    }
  });

  // Toggle on Enter or Space key
  trigger.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      trigger.click();
    }
  });

  // Global ESC key handler to close tooltip
  const escHandler = (e) => {
    if (e.key === 'Escape' && !tooltip.hidden) {
      tooltip.hidden = true;
      trigger.setAttribute('aria-expanded', 'false');
      trigger.focus(); // Return focus to trigger
      e.stopPropagation();
    }
  };

  // Add ESC handler when tooltip is shown
  document.addEventListener('keydown', escHandler);

  // Close tooltip when clicking outside
  document.addEventListener('click', (e) => {
    if (!container.contains(e.target) && !tooltip.hidden) {
      tooltip.hidden = true;
      trigger.setAttribute('aria-expanded', 'false');
    }
  });

  container.appendChild(trigger);
  container.appendChild(tooltip);
  return container;
}

/**
 * Create FAQ accordion component with keyboard accessibility
 * @param {Array<{question: string, answer: string}>} questions - Array of FAQ items
 * @returns {HTMLElement} FAQ accordion container
 */
export function createFAQ(questions) {
  // Create section container
  const section = document.createElement('section');
  section.className = 'faq-section';
  section.setAttribute('aria-labelledby', 'faq-heading');

  // Create heading
  const heading = document.createElement('h2');
  heading.id = 'faq-heading';
  heading.className = 'section-title';
  heading.textContent = 'Vanlige spørsmål';
  section.appendChild(heading);

  // Create FAQ items
  questions.forEach((item, index) => {
    const faqItem = document.createElement('div');
    faqItem.className = 'faq-item';

    const questionId = `faq-question-${index}`;
    const answerId = `faq-answer-${index}`;

    // Create question button
    const questionButton = document.createElement('button');
    questionButton.type = 'button';
    questionButton.id = questionId;
    questionButton.className = 'faq-question';
    questionButton.textContent = item.question;
    questionButton.setAttribute('aria-expanded', 'false');
    questionButton.setAttribute('aria-controls', answerId);

    // Create answer container
    const answerDiv = document.createElement('div');
    answerDiv.id = answerId;
    answerDiv.className = 'faq-answer';
    answerDiv.hidden = true;

    // Support HTML content in answers
    const answerPara = document.createElement('p');
    answerPara.textContent = item.answer;
    answerDiv.appendChild(answerPara);

    // Toggle answer visibility on click
    questionButton.addEventListener('click', () => {
      const isExpanded =
        questionButton.getAttribute('aria-expanded') === 'true';
      questionButton.setAttribute('aria-expanded', (!isExpanded).toString());
      answerDiv.hidden = isExpanded;
    });

    // Toggle on Enter or Space key
    questionButton.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        questionButton.click();
      }
    });

    faqItem.appendChild(questionButton);
    faqItem.appendChild(answerDiv);
    section.appendChild(faqItem);
  });

  return section;
}

/**
 * Close all open tooltips (helper function)
 * @private
 */
function closeAllTooltips() {
  const allTooltips = document.querySelectorAll('.tooltip-content');
  allTooltips.forEach((tooltip) => {
    tooltip.hidden = true;
    const trigger = tooltip.previousElementSibling;
    if (trigger && trigger.classList.contains('tooltip-trigger')) {
      trigger.setAttribute('aria-expanded', 'false');
    }
  });
}
