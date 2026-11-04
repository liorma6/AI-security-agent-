import js from '@eslint/js';
import globals from 'globals';
import hooks from 'eslint-plugin-react-hooks';

export default [
  { ignores: ['**/dist/**', '**/.venv/**', 'test-results/**', 'playwright-report/**'] },
  js.configs.recommended,
  {
    files: ['**/*.{js,mjs,jsx}'],
    ignores: ['apps/web/src/**'],
    languageOptions: { globals: globals.node },
  },
  {
    files: ['apps/web/src/**/*.{js,jsx}'],
    languageOptions: {
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: globals.browser,
    },
    plugins: { 'react-hooks': hooks },
    rules: {
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'error',
    },
  },
  { files: ['tests/e2e/**/*.js'], languageOptions: { globals: globals.browser } },
];
