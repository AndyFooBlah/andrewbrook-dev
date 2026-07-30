# andrewbrook.dev

Personal site + blog. [Astro](https://astro.build), static, deployed to GitHub Pages
on every push to `main` (`.github/workflows/deploy.yml`).

```bash
npm install
npm run dev        # http://localhost:4321
npm run build      # -> dist/
```

## Writing a post

Create `src/content/posts/<slug>.md`. The slug is the URL: `/writing/<slug>/`.

```markdown
---
title: 'Post title'
description: >-
  One or two sentences. Shows up in listings, RSS, and social cards.
date: 2026-07-28
repos:            # optional — renders "Code: …" links, and lists the post on /projects
  - agent-time-bench
tags: [benchmarks, agents]
draft: false      # true keeps it out of listings, RSS, and the sitemap
---

Body in Markdown. Code fences get syntax highlighting in both light and dark.
```

Register a repo slug once in [`src/consts.ts`](src/consts.ts) (`REPOS`) and every
post can reference it.

## Charts and images

**Posts live here; generated charts live in the project repo that produces them.**
Regenerate charts there, then sync:

```bash
./scripts/sync-charts.sh        # copies ../<repo>/blog/charts -> public/charts/<repo>/
```

Reference them with a figure so wide charts scroll instead of squashing:

```html
<figure class="chart">
  <img src="/charts/agent-time-bench/args-dumbbell.svg" alt="Describe what the chart shows" />
</figure>
```

Charts are authored on a light surface, so `.chart` keeps a light background in
dark mode deliberately. Always write real alt text.

## Domain

`public/CNAME` holds `andrewbrook.dev`. DNS: four `A` records for the apex to
GitHub Pages (185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153)
plus a `CNAME` for `www` → `andyfooblah.github.io`.
