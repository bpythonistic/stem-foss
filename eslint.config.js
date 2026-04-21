import { defineConfig } from 'eslint-define-config';
import react from 'eslint-plugin-react';
import reacthooks from 'eslint-plugin-react-hooks';
import reactrefresh from 'eslint-plugin-react-refresh';
import typescript from '@typescript-eslint/eslint-plugin';
import parser from '@typescript-eslint/parser';
import prettier from 'eslint-plugin-prettier';
import plugin from 'eslint-plugin-import';
import a11y from 'eslint-plugin-jsx-a11y';

export default defineConfig({
  files: ['**/*.js', '**/*.jsx', '**/*.ts', '**/*.tsx'],
  languageOptions: {
    parser: parser,
  },
  plugins: {
    react: react,
    reacthooks: reacthooks,
    typescript: typescript,
    reactrefresh: reactrefresh,
    plugin: plugin,
    a11y: a11y,
    prettier: prettier,
  },
  settings: {
    react: {
      version: 'detect',
    },
  },
});
