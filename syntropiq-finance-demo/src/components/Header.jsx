import React from 'react'
import { COLORS, STATUS_COLORS } from '../utils/colors'
import { formatTrust, formatDate } from '../utils/formatters'

const styles = {
  header: {
    position: 'fixed', top: 0, left: 0, right: 0, zIndex: 1000,
    background: 'rgba(10, 14, 26, 0.95)',
    backdropFilter: 'blur(12px)',
    borderBottom: `1px solid ${COLORS.border}`,
    padding: '0 24px',
    height: 64,
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  },
  left: { display: 'flex', alignItems: 'center', gap: 16 },
  logo: {
    fontSize: 18, fontWeight: 700, color: COLORS.blue,
    letterSpacing: '-0.5px',
  },
  title: {
    fontSize: 13, color: COLORS.textMuted, fontWeight: 500,
    borderLeft: `1px solid ${COLORS.border}`, paddingLeft: 16,
  },
  center: { display: 'flex', gap: 12, alignItems: 'center' },
  pill: {
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '4px 12px', borderRadius: 4,
    background: COLORS.bgCard, border: `1px solid ${COLORS.border}`,
    fontSize: 12, fontWeight: 500,
  },
  dot: {
    width: 6, height: 6, borderRadius: '50%',
  },
  right: { display: 'flex', alignItems: 'center', gap: 16 },
  weekCounter: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 13, color: COLORS.text, fontWeight: 500,
  },
  regimePill: {
    padding: '4px 10px', borderRadius: 3,
    fontSize: 11, fontWeight: 600, letterSpacing: '0.5px',
    textTransform: 'uppercase',
  },
}

const AGENT_LABELS = { growth: 'Growth', risk: 'Risk', macro: 'Macro' }
const AGENT_COLORS = { growth: COLORS.growth, risk: COLORS.risk, macro: COLORS.macro }

export default function Header({ sim, summary }) {
  const { currentData, currentWeek, totalWeeks } = sim
  const agents = currentData?.agents || {}
  const regime = currentData?.regime || 'bull'
  const date = currentData?.date || '2021-01-04'

  return (
    <div style={styles.header}>
      <div style={styles.left}>
        <div style={styles.logo}>SYNTROPIQ</div>
        <div style={styles.title}>Adaptive Allocation Governance Engine</div>
      </div>

      <div style={styles.center}>
        {Object.entries(AGENT_LABELS).map(([id, label]) => {
          const agent = agents[id]
          const status = agent?.status || 'active'
          const trust = agent?.trust ?? 0.75
          const color = STATUS_COLORS[status] || COLORS.green

          return (
            <div key={id} style={styles.pill}>
              <div style={{ ...styles.dot, background: color }} />
              <span style={{ color: AGENT_COLORS[id] }}>{label}</span>
              <span style={{ color: COLORS.textMuted }}>{formatTrust(trust)}</span>
              <span style={{
                fontSize: 10, color, fontWeight: 600,
                textTransform: 'uppercase',
              }}>
                {status}
              </span>
            </div>
          )
        })}
      </div>

      <div style={styles.right}>
        <div style={styles.weekCounter}>
          WEEK {String(currentWeek).padStart(2, '0')} / {totalWeeks}
        </div>
        <div style={{ fontSize: 12, color: COLORS.textMuted }}>
          {formatDate(date)}
        </div>
        <div style={{
          ...styles.regimePill,
          background: regime === 'bull'
            ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)',
          color: regime === 'bull' ? COLORS.green : COLORS.red,
          border: `1px solid ${regime === 'bull' ? COLORS.green : COLORS.red}33`,
        }}>
          {regime === 'bull' ? 'Bull Regime' : 'Stress Regime'}
        </div>
      </div>
    </div>
  )
}
