import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Em desenvolvimento (npm run dev), as chamadas /api vão para o gateway do Docker.
    proxy: { '/api': 'http://localhost' },
  },
});
