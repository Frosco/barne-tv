/**
 * Help Component Tests
 * Story 3.X: Admin Help & Documentation
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { createTooltip, createFAQ } from './help.js';

describe('createTooltip', () => {
  let container;

  beforeEach(() => {
    // Create a clean DOM for each test
    document.body.innerHTML = '';
    container = null;
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('should render trigger button with correct text', () => {
    container = createTooltip('ℹ️', 'Test help text', 'test-tooltip');
    expect(container).toBeTruthy();

    const trigger = container.querySelector('.tooltip-trigger');
    expect(trigger).toBeTruthy();
    expect(trigger.textContent).toBe('ℹ️');
  });

  it('should create tooltip element with role="tooltip"', () => {
    container = createTooltip('ℹ️', 'Test help text', 'test-tooltip');

    const tooltip = container.querySelector('.tooltip-content');
    expect(tooltip).toBeTruthy();
    expect(tooltip.getAttribute('role')).toBe('tooltip');
    expect(tooltip.id).toBe('test-tooltip');
    expect(tooltip.textContent).toBe('Test help text');
  });

  it('should set correct ARIA attributes', () => {
    container = createTooltip('ℹ️', 'Test help text', 'test-tooltip');

    const trigger = container.querySelector('.tooltip-trigger');
    expect(trigger.getAttribute('aria-describedby')).toBe('test-tooltip');
    expect(trigger.getAttribute('aria-expanded')).toBe('false');
    expect(trigger.getAttribute('aria-label')).toBe('Vis hjelpetekst');
  });

  it('should toggle tooltip visibility on click', () => {
    container = createTooltip('ℹ️', 'Test help text', 'test-tooltip');
    document.body.appendChild(container);

    const trigger = container.querySelector('.tooltip-trigger');
    const tooltip = container.querySelector('.tooltip-content');

    // Initially hidden
    expect(tooltip.hidden).toBe(true);

    // Click to show
    trigger.click();
    expect(tooltip.hidden).toBe(false);
    expect(trigger.getAttribute('aria-expanded')).toBe('true');

    // Click to hide
    trigger.click();
    expect(tooltip.hidden).toBe(true);
    expect(trigger.getAttribute('aria-expanded')).toBe('false');
  });

  it('should toggle tooltip on Enter key', () => {
    container = createTooltip('ℹ️', 'Test help text', 'test-tooltip');
    document.body.appendChild(container);

    const trigger = container.querySelector('.tooltip-trigger');
    const tooltip = container.querySelector('.tooltip-content');

    // Press Enter to show
    const enterEvent = new KeyboardEvent('keydown', { key: 'Enter' });
    trigger.dispatchEvent(enterEvent);

    expect(tooltip.hidden).toBe(false);
    expect(trigger.getAttribute('aria-expanded')).toBe('true');
  });

  it('should toggle tooltip on Space key', () => {
    container = createTooltip('ℹ️', 'Test help text', 'test-tooltip');
    document.body.appendChild(container);

    const trigger = container.querySelector('.tooltip-trigger');
    const tooltip = container.querySelector('.tooltip-content');

    // Press Space to show
    const spaceEvent = new KeyboardEvent('keydown', { key: ' ' });
    trigger.dispatchEvent(spaceEvent);

    expect(tooltip.hidden).toBe(false);
    expect(trigger.getAttribute('aria-expanded')).toBe('true');
  });

  it('should close tooltip on ESC key', () => {
    container = createTooltip('ℹ️', 'Test help text', 'test-tooltip');
    document.body.appendChild(container);

    const trigger = container.querySelector('.tooltip-trigger');
    const tooltip = container.querySelector('.tooltip-content');

    // Open tooltip first
    trigger.click();
    expect(tooltip.hidden).toBe(false);

    // Press ESC to close
    const escEvent = new KeyboardEvent('keydown', { key: 'Escape' });
    document.dispatchEvent(escEvent);

    expect(tooltip.hidden).toBe(true);
    expect(trigger.getAttribute('aria-expanded')).toBe('false');
  });

  it('should close tooltip when clicking outside', () => {
    container = createTooltip('ℹ️', 'Test help text', 'test-tooltip');
    document.body.appendChild(container);

    const trigger = container.querySelector('.tooltip-trigger');
    const tooltip = container.querySelector('.tooltip-content');

    // Open tooltip
    trigger.click();
    expect(tooltip.hidden).toBe(false);

    // Click outside
    document.body.click();

    expect(tooltip.hidden).toBe(true);
    expect(trigger.getAttribute('aria-expanded')).toBe('false');
  });
});

describe('createFAQ', () => {
  let section;

  beforeEach(() => {
    document.body.innerHTML = '';
    section = null;
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  const sampleQuestions = [
    {
      question: 'Hvordan legger jeg til en ny kanal?',
      answer: 'Gå til Kanaler-fanen og lim inn kanal URL.',
    },
    {
      question: 'Hva er forskjellen på kanaler og spillelister?',
      answer:
        'Kanaler inneholder alle videoer. Spillelister er kuraterte samlinger.',
    },
  ];

  it('should render section with correct heading', () => {
    section = createFAQ(sampleQuestions);
    expect(section).toBeTruthy();

    const heading = section.querySelector('#faq-heading');
    expect(heading).toBeTruthy();
    expect(heading.textContent).toBe('Vanlige spørsmål');
    expect(section.getAttribute('aria-labelledby')).toBe('faq-heading');
  });

  it('should render question buttons with correct text', () => {
    section = createFAQ(sampleQuestions);

    const questions = section.querySelectorAll('.faq-question');
    expect(questions.length).toBe(2);
    expect(questions[0].textContent).toBe(sampleQuestions[0].question);
    expect(questions[1].textContent).toBe(sampleQuestions[1].question);
  });

  it('should set correct ARIA attributes on questions', () => {
    section = createFAQ(sampleQuestions);

    const question1 = section.querySelector('#faq-question-0');
    expect(question1.getAttribute('aria-expanded')).toBe('false');
    expect(question1.getAttribute('aria-controls')).toBe('faq-answer-0');
  });

  it('should toggle answer visibility on click', () => {
    section = createFAQ(sampleQuestions);
    document.body.appendChild(section);

    const question = section.querySelector('#faq-question-0');
    const answer = section.querySelector('#faq-answer-0');

    // Initially hidden
    expect(answer.hidden).toBe(true);
    expect(question.getAttribute('aria-expanded')).toBe('false');

    // Click to show
    question.click();
    expect(answer.hidden).toBe(false);
    expect(question.getAttribute('aria-expanded')).toBe('true');

    // Click to hide
    question.click();
    expect(answer.hidden).toBe(true);
    expect(question.getAttribute('aria-expanded')).toBe('false');
  });

  it('should toggle answer on Enter key', () => {
    section = createFAQ(sampleQuestions);
    document.body.appendChild(section);

    const question = section.querySelector('#faq-question-0');
    const answer = section.querySelector('#faq-answer-0');

    // Press Enter to show
    const enterEvent = new KeyboardEvent('keydown', { key: 'Enter' });
    question.dispatchEvent(enterEvent);

    expect(answer.hidden).toBe(false);
    expect(question.getAttribute('aria-expanded')).toBe('true');
  });

  it('should toggle answer on Space key', () => {
    section = createFAQ(sampleQuestions);
    document.body.appendChild(section);

    const question = section.querySelector('#faq-question-0');
    const answer = section.querySelector('#faq-answer-0');

    // Press Space to show
    const spaceEvent = new KeyboardEvent('keydown', { key: ' ' });
    question.dispatchEvent(spaceEvent);

    expect(answer.hidden).toBe(false);
    expect(question.getAttribute('aria-expanded')).toBe('true');
  });

  it('should display answer content correctly', () => {
    section = createFAQ(sampleQuestions);

    const answer = section.querySelector('#faq-answer-0 p');
    expect(answer).toBeTruthy();
    expect(answer.textContent).toBe(sampleQuestions[0].answer);
  });

  it('should handle multiple FAQ items independently', () => {
    section = createFAQ(sampleQuestions);
    document.body.appendChild(section);

    const question1 = section.querySelector('#faq-question-0');
    const answer1 = section.querySelector('#faq-answer-0');
    const question2 = section.querySelector('#faq-question-1');
    const answer2 = section.querySelector('#faq-answer-1');

    // Open first FAQ
    question1.click();
    expect(answer1.hidden).toBe(false);
    expect(answer2.hidden).toBe(true);

    // Open second FAQ (first should stay open)
    question2.click();
    expect(answer1.hidden).toBe(false);
    expect(answer2.hidden).toBe(false);

    // Close first FAQ
    question1.click();
    expect(answer1.hidden).toBe(true);
    expect(answer2.hidden).toBe(false);
  });
});
