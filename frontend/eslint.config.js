// ESLint flat configuration (ESLint 9.x)
// https://eslint.org/docs/latest/use/configure/configuration-files

import js from '@eslint/js';
import globals from 'globals';

export default [
  // Apply to all JavaScript files
  {
    files: ['src/**/*.js'],
    languageOptions: {
      ecmaVersion: 2021,
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.es2021,
      },
    },
    rules: {
      ...js.configs.recommended.rules,
      'no-unused-vars': 'error',
      'no-undef': 'error',
      'require-await': 'error',
      'no-shadow': 'warn',
      'no-console': 'off',
    },
  },
];
