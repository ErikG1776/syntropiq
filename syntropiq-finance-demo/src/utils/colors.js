export const COLORS = {
  bg: '#0a0e1a',
  bgCard: '#111827',
  bgCardHover: '#1a2235',
  bgPanel: '#0d1117',
  border: '#1e293b',
  borderLight: '#334155',
  text: '#e2e8f0',
  textMuted: '#94a3b8',
  textDim: '#64748b',
  blue: '#3b82f6',
  blueLight: '#60a5fa',
  green: '#22c55e',
  greenLight: '#4ade80',
  red: '#ef4444',
  redLight: '#f87171',
  amber: '#f59e0b',
  amberLight: '#fbbf24',
  purple: '#a855f7',
  purpleLight: '#c084fc',
  white: '#ffffff',
  // Agent colors
  growth: '#ef4444',
  risk: '#3b82f6',
  macro: '#22c55e',
  benchmark: '#64748b',
}

export const STATUS_COLORS = {
  active: COLORS.green,
  probation: COLORS.amber,
  suppressed: COLORS.red,
}

export const EVENT_COLORS = {
  trust_increase: COLORS.blue,
  trust_decrease: COLORS.amber,
  trust_decrease_moderate: COLORS.amber,
  trust_decrease_severe: COLORS.red,
  suppression: COLORS.red,
  probation: COLORS.amber,
  redemption: COLORS.green,
  recovery: COLORS.green,
  mutation: COLORS.purple,
  regime_shift: COLORS.purple,
}
