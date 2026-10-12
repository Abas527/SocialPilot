import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
    },
  },
  {
    // Context modules intentionally export a provider component and its hook together.
    files: [
      'src/auth/AuthContext.tsx', 'src/jobs/JobsProvider.tsx', 'src/theme/ThemeContext.tsx',
      'src/components/Flash.tsx', 'src/components/community/ComposeContext.tsx',
    ],
    rules: { 'react-refresh/only-export-components': 'off' },
  },
])
