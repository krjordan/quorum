import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    // Test environment
    environment: 'jsdom',

    // Setup files
    setupFiles: ['./tests/frontend/setup.ts'],

    // Global test utilities
    globals: true,

    // Coverage configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      reportsDirectory: './tests/coverage/frontend',
      exclude: [
        'node_modules/',
        'tests/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/mockData/**',
        'dist/',
        '.eslintrc.cjs'
      ],
      include: ['src/**/*.{ts,tsx}'],
      all: true,
      lines: 80,
      functions: 80,
      branches: 80,
      statements: 80,
      // Check coverage thresholds
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80
      }
    },

    // Test matching patterns
    include: ['tests/frontend/**/*.{test,spec}.{ts,tsx}'],
    exclude: ['node_modules', 'dist', '.idea', '.git', '.cache'],

    // Reporters
    reporters: ['verbose', 'html'],
    outputFile: {
      html: './tests/coverage/frontend/index.html'
    },

    // Timeouts
    testTimeout: 10000,
    hookTimeout: 10000,

    // Concurrency
    threads: true,
    maxThreads: 4,
    minThreads: 1,

    // Watch mode
    watch: false,

    // Mocking
    mockReset: true,
    clearMocks: true,
    restoreMocks: true,

    // Environment variables
    env: {
      NODE_ENV: 'test',
      VITE_API_URL: 'http://localhost:8000'
    }
  },

  // Path resolution
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
      '@services': path.resolve(__dirname, './src/services'),
      '@utils': path.resolve(__dirname, './src/utils'),
      '@types': path.resolve(__dirname, './src/types'),
      '@test-utils': path.resolve(__dirname, './tests/frontend/utils')
    }
  }
});
