import raw from '../data/coding-stats.json';

export type Week = (typeof raw.weeks)[number];
export const stats = raw;

export const CHORE_LABELS: Record<string, string> = {
  'cloud-infra': 'Cloud infra config',
  'secrets-auth': 'Secrets & auth',
  'accounts-billing': 'Accounts & billing',
  'dns-deploy': 'DNS & deploys',
  'manual-testing': 'Manual testing',
  other: 'Other',
};

export const SPEND_LABELS: Record<string, string> = {
  claude: 'Claude',
  cloud: 'Cloud',
  other: 'Other',
};

/** Last `n` weeks, oldest first. */
export function recentWeeks(n: number): Week[] {
  return raw.weeks.slice(-n);
}

export function lines(w: Week, who: 'ai' | 'hand'): number {
  return w[`${who}_added`] + w[`${who}_deleted`];
}

export function chores(w: Week): number {
  return Object.values(w.chores).reduce((a, b) => a + b, 0);
}

export function spend(w: Week): number {
  return Object.values(w.spend).reduce((a, b) => a + b, 0);
}

/** Claude hours: transcript minutes plus the per-web-session estimate. */
export function claudeHours(w: Week): number {
  return (w.claude_minutes + w.web_sessions * raw.web_session_minutes) / 60;
}

export function totals(weeks: Week[]) {
  const sum = (f: (w: Week) => number) => weeks.reduce((a, w) => a + f(w), 0);
  const ai = sum((w) => lines(w, 'ai'));
  const hand = sum((w) => lines(w, 'hand'));
  const byChore: Record<string, number> = {};
  for (const c of raw.chore_categories) byChore[c] = sum((w) => w.chores[c as keyof Week['chores']]);
  return {
    ai,
    hand,
    aiShare: ai + hand ? ai / (ai + hand) : 0,
    aiCommits: sum((w) => w.ai_commits),
    handCommits: sum((w) => w.hand_commits),
    hours: sum(claudeHours),
    sessions: sum((w) => w.sessions + w.web_sessions),
    chores: sum(chores),
    choreMinutes: sum((w) => w.chore_minutes),
    spend: sum(spend),
    byChore,
  };
}

/** 1,284 → "1.3K", 4200000 → "4.2M". */
export function compact(n: number): string {
  if (Math.abs(n) >= 1e6) return `${(n / 1e6).toFixed(1).replace(/\.0$/, '')}M`;
  if (Math.abs(n) >= 1e4) return `${Math.round(n / 1e3)}K`;
  if (Math.abs(n) >= 1e3) return `${(n / 1e3).toFixed(1).replace(/\.0$/, '')}K`;
  return Math.round(n).toLocaleString('en-US');
}

export function usd(n: number): string {
  return n >= 1000 ? `$${compact(n)}` : `$${Math.round(n).toLocaleString('en-US')}`;
}

export function pct(x: number): string {
  return `${Math.round(x * 100)}%`;
}

/** Axis ticks with a clean step (1/2/2.5/5 × 10^k); the last tick is the axis max. */
export function niceTicks(max: number, count = 4): number[] {
  if (max <= 0) return [1];
  const raw = max / count;
  const p = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * p).find((s) => s >= raw) ?? 10 * p;
  const n = Math.ceil(max / step);
  return Array.from({ length: n }, (_, i) => (i + 1) * step);
}

/** Clean axis max: smallest 1/2/5 × 10^k ≥ max (at least 1). */
export function niceMax(max: number): number {
  if (max <= 0) return 1;
  const p = Math.pow(10, Math.floor(Math.log10(max)));
  for (const m of [1, 2, 2.5, 5, 10]) if (m * p >= max) return m * p;
  return 10 * p;
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** Label a week only when it's the first week that touches a new month. */
export function monthLabels(weeks: Week[]): string[] {
  let last = '';
  const out = weeks.map((w) => {
    const d = new Date(w.week + 'T00:00:00Z');
    d.setUTCDate(d.getUTCDate() + 6); // week end decides the month
    const key = `${d.getUTCFullYear()}-${d.getUTCMonth()}`;
    if (key === last) return '';
    last = key;
    return MONTHS[d.getUTCMonth()];
  });
  // A label needs ~3 slots of room; drop one when the next is closer than that.
  for (let i = 0; i < out.length; i++) {
    if (out[i] && (out[i + 1] || out[i + 2])) out[i] = '';
  }
  return out;
}

export function weekRange(w: Week): string {
  const a = new Date(w.week + 'T00:00:00Z');
  const b = new Date(a);
  b.setUTCDate(a.getUTCDate() + 6);
  const f = (d: Date) => `${MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}`;
  return `${f(a)} – ${f(b)}, ${b.getUTCFullYear()}`;
}
