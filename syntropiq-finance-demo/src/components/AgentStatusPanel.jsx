import React, { useState, useEffect } from 'react'
import { COLORS, STATUS_COLORS } from '../utils/colors'
import { formatTrust, formatWeight, formatPctRaw } from '../utils/formatters'

const AGENT_META = {
  growth: { label: 'Growth Agent', color: COLORS.growth },
  risk: { label: 'Risk Agent', color: COLORS.risk },
  macro: { label: 'Macro Agent', color: COLORS.macro },
}

const styles = {
  grid: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 },
  card: {
    background: COLORS.bgCard, border: `1px solid ${COLORS.border}`,
    overflow: 'hidden', transition: 'all 0.3s ease', position: 'relative',
  },
  header: {
    padding: '12px 16px', display: 'flex', alignItems: 'center',
    justifyContent: 'space-between',
  },
  agentName: { fontSize: 14, fontWeight: 600 },
  badge: {
    padding: '2px 8px', borderRadius: 3, fontSize: 10,
    fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px',
  },
  body: { padding: '0 16px 16px' },
  metricRow: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
    marginBottom: 12,
  },
  metricLabel: {
    fontSize: 11, color: COLORS.textMuted, textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  metricValue: {
    fontSize: 22, fontWeight: 700,
    fontFamily: "'JetBrains Mono', monospace",
  },
  sparkline: {
    height: 40, display: 'flex', alignItems: 'flex-end', gap: 1,
    marginBottom: 12,
  },
  sparkBar: {
    flex: 1, borderRadius: '1px 1px 0 0', transition: 'height 0.3s ease',
  },
  allocation: { marginTop: 8 },
  allocBar: {
    height: 6, display: 'flex', borderRadius: 3, overflow: 'hidden',
  },
  allocLabel: {
    display: 'flex', justifyContent: 'space-between',
    fontSize: 10, color: COLORS.textMuted, marginTop: 4,
  },
  suppressedOverlay: {
    position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
    background: 'rgba(10, 14, 26, 0.6)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    zIndex: 2, transition: 'opacity 0.3s ease',
  },
  suppressedLabel: {
    color: COLORS.red, fontSize: 14, fontWeight: 700,
    letterSpacing: '2px', textTransform: 'uppercase',
    border: `2px solid ${COLORS.red}`, padding: '6px 16px',
    background: 'rgba(239, 68, 68, 0.1)',
  },
}

const ALLOC_COLORS = {
  QQQ: '#a855f7', SPY: '#3b82f6', TLT: '#22c55e',
}

function SparkLine({ history, color }) {
  const last12 = history.slice(-12)
  const max = Math.max(...last12, 0.01)
  return (
    <div style={styles.sparkline}>
      {last12.map((v, i) => (
        <div key={i} style={{
          ...styles.sparkBar,
          height: `${Math.max(2, (v / max) * 100)}%`,
          background: `${color}${i === last12.length - 1 ? '' : '88'}`,
        }} />
      ))}
    </div>
  )
}

export default function AgentStatusPanel({ sim }) {
  const { currentData, visibleTimeline } = sim
  const [flashAgent, setFlashAgent] = useState(null)

  // Detect status changes for flash animation
  useEffect(() => {
    if (visibleTimeline.length < 2) return
    const prev = visibleTimeline[visibleTimeline.length - 2]
    const curr = visibleTimeline[visibleTimeline.length - 1]
    if (!prev || !curr) return
    for (const id of ['growth', 'risk', 'macro']) {
      if (prev.agents[id].status !== curr.agents[id].status) {
        setFlashAgent(id)
        setTimeout(() => setFlashAgent(null), 800)
        break
      }
    }
  }, [visibleTimeline.length])

  return (
    <div style={styles.grid}>
      {Object.entries(AGENT_META).map(([id, meta]) => {
        const agent = currentData?.agents?.[id] || {
          trust: 0.75, authority_weight: 0.333, status: 'active',
          weekly_return: 0, benchmark_delta: 0,
          allocation: { QQQ: 0.33, SPY: 0.33, TLT: 0.34 },
        }
        const status = agent.status
        const statusColor = STATUS_COLORS[status] || COLORS.green
        const isSuppressed = status === 'suppressed'
        const isFlashing = flashAgent === id

        // Build trust history from visible timeline
        const trustHistory = visibleTimeline.map(w => w.agents[id].trust)

        // Delta arrow
        const deltaSign = agent.benchmark_delta >= 0
        const deltaColor = deltaSign ? COLORS.green : COLORS.red
        const deltaArrow = deltaSign ? '↑' : '↓'

        return (
          <div key={id} style={{
            ...styles.card,
            borderColor: isFlashing
              ? (status === 'suppressed' ? COLORS.red : COLORS.green) : COLORS.border,
            boxShadow: isFlashing
              ? `0 0 20px ${status === 'suppressed' ? COLORS.red : COLORS.green}44` : 'none',
          }}>
            <div style={{ ...styles.header, borderBottom: `2px solid ${meta.color}` }}>
              <span style={{ ...styles.agentName, color: meta.color }}>{meta.label}</span>
              <span style={{
                ...styles.badge,
                background: `${statusColor}22`,
                color: statusColor,
                border: `1px solid ${statusColor}44`,
              }}>
                {status}
              </span>
            </div>

            <div style={styles.body}>
              <div style={styles.metricRow}>
                <div>
                  <div style={styles.metricLabel}>Trust Score</div>
                  <div style={{ ...styles.metricValue, color: meta.color }}>
                    {formatTrust(agent.trust)}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={styles.metricLabel}>Authority</div>
                  <div style={{ ...styles.metricValue, fontSize: 18, color: COLORS.text }}>
                    {formatWeight(agent.authority_weight)}
                  </div>
                </div>
              </div>

              <div style={{ marginBottom: 8 }}>
                <div style={styles.metricLabel}>Weekly vs Benchmark</div>
                <div style={{
                  fontSize: 16, fontWeight: 600, color: deltaColor,
                  fontFamily: "'JetBrains Mono', monospace",
                }}>
                  {deltaArrow} {formatPctRaw(agent.benchmark_delta)}
                </div>
              </div>

              <div style={styles.metricLabel}>Trust History (last 12 weeks)</div>
              <SparkLine history={trustHistory} color={meta.color} />

              <div style={styles.metricLabel}>Allocation</div>
              <div style={styles.allocBar}>
                {Object.entries(agent.allocation).map(([ticker, weight]) => (
                  <div key={ticker} style={{
                    width: `${weight * 100}%`,
                    background: ALLOC_COLORS[ticker] || COLORS.textDim,
                  }} />
                ))}
              </div>
              <div style={styles.allocLabel}>
                {Object.entries(agent.allocation).map(([ticker, weight]) => (
                  <span key={ticker}>{ticker} {(weight * 100).toFixed(0)}%</span>
                ))}
              </div>
            </div>

            {isSuppressed && (
              <div style={styles.suppressedOverlay}>
                <div style={styles.suppressedLabel}>SUPPRESSED</div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
