export default {
  build: {
    outDir: '../static',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        child: './src/child.js',
        admin: './src/admin.js'
      }
    }
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
    }
  },
  publicDir: 'public'
}
