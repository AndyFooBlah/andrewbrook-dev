export const SITE = {
  title: 'Andrew Brook',
  description:
    'Notes on building software — libraries, agents, benchmarks, and what the data actually said.',
  author: 'Andrew Brook',
  url: 'https://andrewbrook.dev',
  github: 'https://github.com/AndyFooBlah',
  linkedin: 'https://www.linkedin.com/in/andrewbrook/',
};

/** Themes group the projects page, in display order. */
export const THEMES = [
  {
    id: 'voice',
    title: 'Voice AI applications',
    blurb: 'Real-time spoken conversation apps built on the Gemini Live API.',
  },
  {
    id: 'libraries',
    title: 'Libraries & utilities',
    blurb: 'Reusable packages extracted from the applications above.',
  },
  {
    id: 'agents',
    title: 'Agents & data',
    blurb: 'Agents that answer questions over real data pipelines.',
  },
  {
    id: 'evaluation',
    title: 'Benchmarks & evaluation',
    blurb: 'Measuring what models and agents actually get right.',
  },
  {
    id: 'site',
    title: 'This site',
    blurb: '',
  },
] as const;

export type ThemeId = (typeof THEMES)[number]['id'];

export interface Project {
  name: string;
  url: string;
  blurb: string;
  theme: ThemeId;
  lang?: string;
  /** Published packages / live deployments worth linking. */
  links?: { label: string; url: string }[];
}

/**
 * Public projects. `repos:` slugs in post frontmatter resolve through this,
 * so a post automatically links to its code and appears under the project.
 */
export const REPOS: Record<string, Project> = {
  carbot: {
    name: 'CarBot',
    url: 'https://github.com/AndyFooBlah/CarBot',
    blurb:
      'A voice-first AI companion for car rides with kids — answers questions, tells jokes, builds a memory of the family over time, and emails parents a recap after each drive.',
    theme: 'voice',
    lang: 'TypeScript',
  },
  legacybot: {
    name: 'LegacyBot / BiographyBot',
    url: 'https://github.com/AndyFooBlah/LegacyBot',
    blurb:
      'Voice-first life-story preservation: conducts empathetic real-time interviews with a storyteller, then transcribes and organizes their narrative for the family archive.',
    theme: 'voice',
    lang: 'TypeScript',
    links: [{ label: 'biographybot.com', url: 'https://biographybot.com' }],
  },
  nl2time: {
    name: 'nl2time',
    url: 'https://github.com/AndyFooBlah/nl2time',
    blurb:
      'Bidirectional natural language ⇄ date/time. Parses "last week" into timezone- and locale-correct intervals and describes instants back as "9pm last night", around a deterministic JSON IR. Six languages; JS and Python.',
    theme: 'libraries',
    lang: 'TypeScript · Python',
    links: [
      { label: 'npm', url: 'https://www.npmjs.com/package/nl2time' },
      { label: 'PyPI', url: 'https://pypi.org/project/nl2time/' },
    ],
  },
  voicecommon: {
    name: 'VoiceCommon',
    url: 'https://github.com/AndyFooBlah/VoiceCommon',
    blurb:
      'A framework for voice AI web apps on Gemini Live and Firebase — session management, transcript archival, audio recording, tool integration. Extracted from LegacyBot and generalized.',
    theme: 'libraries',
    lang: 'TypeScript',
    links: [{ label: 'npm', url: 'https://www.npmjs.com/package/@andyfooblah/voice-common' }],
  },
  knowledgecommon: {
    name: 'KnowledgeCommon',
    url: 'https://github.com/AndyFooBlah/KnowledgeCommon',
    blurb:
      'Shared knowledge tools for Gemini Live voice apps: weather, maps, jokes, Wikipedia RAG, and date/time — with server-side proxying so API keys never reach the browser.',
    theme: 'libraries',
    lang: 'TypeScript',
    links: [{ label: 'npm', url: 'https://www.npmjs.com/package/@andyfooblah/knowledge-common' }],
  },
  weatherbot: {
    name: 'weatherbot',
    url: 'https://github.com/AndyFooBlah/weatherbot',
    blurb:
      'Personal weather data end to end: Ambient Weather Network ingestion into Cloud SQL Postgres, queried in natural language by an ADK agent over MCP Toolbox.',
    theme: 'agents',
    lang: 'Python',
  },
  'weatherbot-app': {
    name: 'weatherbot-app',
    url: 'https://github.com/AndyFooBlah/weatherbot-app',
    blurb:
      'Mobile-first chat and voice frontend for weatherbot — React + Vite on Firebase, talking to the agent through the Gemini Live API.',
    theme: 'agents',
    lang: 'TypeScript',
  },
  'agent-time-bench': {
    name: 'agent-time-bench',
    url: 'https://github.com/AndyFooBlah/agent-time-bench',
    blurb:
      'How well do LLM agents handle date/time in the tool calls they make and the answers they give? 10 domains × 10 scenarios, graded on both directions, across models from tiny open-weights to closed frontier.',
    theme: 'evaluation',
    lang: 'Python',
  },
  'andrewbrook-dev': {
    name: 'andrewbrook-dev',
    url: 'https://github.com/AndyFooBlah/andrewbrook-dev',
    blurb: 'The source of this site — Astro, statically built, deployed to GitHub Pages.',
    theme: 'site',
    lang: 'Astro',
  },
};

/** Upstream projects I contribute to rather than own. */
export const CONTRIBUTIONS = [
  {
    name: 'googleapis/genai-toolbox',
    url: 'https://github.com/googleapis/genai-toolbox',
    blurb: 'MCP Toolbox for Databases — an open-source MCP server for databases.',
  },
];
