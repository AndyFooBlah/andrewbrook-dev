export const SITE = {
  title: 'Andrew Brook',
  description:
    'Notes on building software — libraries, agents, benchmarks, and what the data actually said.',
  author: 'Andrew Brook',
  url: 'https://andrewbrook.dev',
  github: 'https://github.com/AndyFooBlah',
  linkedin: 'https://www.linkedin.com/in/andrewbrook/',
};

/** Repo metadata: `repos:` slugs in post frontmatter resolve through this. */
export const REPOS: Record<string, { name: string; url: string; blurb: string }> = {
  'agent-time-bench': {
    name: 'agent-time-bench',
    url: 'https://github.com/AndyFooBlah/agent-time-bench',
    blurb: 'Benchmark for how well LLM agents handle date/time in tool calls and answers.',
  },
  nl2time: {
    name: 'nl2time',
    url: 'https://github.com/AndyFooBlah/nl2time',
    blurb: 'Bidirectional natural language ⇄ date/time, deterministic, six languages.',
  },
};
