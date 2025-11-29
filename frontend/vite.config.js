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
        'shared/version': './src/shared/version.js',
      },
      output: {
        // Use stable filenames without content hashes for template compatibility
        entryFileNames: 'assets/[name].js',
        chunkFileNames: 'assets/[name].js',
        assetFileNames: 'assets/[name][extname]',
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
