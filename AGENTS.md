# andrewbrook.dev — working notes

Astro static site, deployed to GitHub Pages by `.github/workflows/deploy.yml`.

- **Posts** are Markdown in `src/content/posts/`; schema in `src/content.config.ts`.
  URL is `/writing/<filename>/`.
- **Posts live in THIS repo, not in project repos.** Project repos keep their
  technical docs (design, methodology, results); the blog keeps the narrative
  articles. One feed, one deploy, no cross-repo publishing.
- **Charts are generated artifacts owned by the project repo.** Never hand-edit
  `public/charts/**` — regenerate in the project (e.g.
  `agent-time-bench/scripts/make_charts.py`) then run `./scripts/sync-charts.sh`.
- Styling is one file: `src/styles/global.css`. Light and dark are both
  explicitly specified; the toggle stamps `data-theme` on `<html>` and must win
  over the OS preference in both directions.
- Dev server: `npm run dev` (port 4321). Verify posts render before committing —
  especially charts and tables (wide content must scroll inside its own box, and
  the page body must never scroll horizontally).
