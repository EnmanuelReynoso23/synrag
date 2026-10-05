import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// En Vercel, VERCEL_PROJECT_PRODUCTION_URL trae el dominio sin https://.
// Para otro dominio: VITE_SITE_URL=https://synrag.dev
const urlSitio = (
  process.env.VITE_SITE_URL ||
  (process.env.VERCEL_PROJECT_PRODUCTION_URL ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}` : '')
).replace(/\/$/, '')

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    {
      name: 'url-del-sitio',
      transformIndexHtml: (html) => html.replaceAll('%SITE_URL%', urlSitio),
    },
  ],
})
