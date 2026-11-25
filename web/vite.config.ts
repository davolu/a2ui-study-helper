import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';

// During `npm run dev`, send /api calls to the Python agent on port 8000.
export default defineConfig({
  plugins: [react()],
  server: {proxy: {'/api': 'http://127.0.0.1:8000'}},
});
