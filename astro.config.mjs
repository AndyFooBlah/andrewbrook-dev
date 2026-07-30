// @ts-check
import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://andrewbrook.dev',
  markdown: {
    shikiConfig: {
      // Both themes ship; the CSS in global.css picks one per color scheme.
      themes: { light: 'github-light', dark: 'github-dark' },
      wrap: false,
    },
  },
});
