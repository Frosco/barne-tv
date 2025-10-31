import { readFileSync } from 'fs';

// Read version from package.json (Story 3.X)
const packageJson = JSON.parse(readFileSync('./package.json', 'utf-8'));

export default {
  build: {
    outDir: '../static',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        child: './src/child.js',
        admin: './src/admin.js',
      },
    },
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  publicDir: 'public',
  define: {
    'import.meta.env.VITE_APP_VERSION': JSON.stringify(packageJson.version),
  },
};
