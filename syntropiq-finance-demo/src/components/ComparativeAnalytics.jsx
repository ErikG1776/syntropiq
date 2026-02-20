import React from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { COLORS } from '../utils/colors'
import { formatDollar, formatPct } from '../utils/formatters'

const styles = {
  grid: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 },
  panel: {
    background: COLORS.bgCard, border: `1px solid ${COLORS.border}`,
    padding: 20,
  },
  panelTitle: {
    fontSize: 13, fontWeight: 600, color: COLORS.text,
    marginBottom: 16,
  },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 12 },
  th: {
    textAlign: 'left', padding: '6px 8px', color: COLORS.textMuted,
    borderBottom: `1px solid ${COLORS.border}`, fontSize: 11,
    fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px',
  },
  td: {
    padding: '6px 8px', borderBottom: `1px solid ${COLORS.border}11`,
    fontFamily: "'JetBrains Mono', monospace",
  },
  timelineRow: {
    display: 'flex', alignItems: 'center', gap: 4,
    marginBottom: 8,
  },
  timelineLabel: {
    width: 60, fontSize: 11, color: COLORS.textMuted, textAlign: 'right',
    paddingRight: 8,
  },
  timelineBar: {
    flex: 1, height: 16, display: 'flex', borderRadius: 2,
    overflow: 'hidden', background: COLORS.bgPanel,
  },
  payloadPanel: {
    background: COLORS.bgCard, border: `1px solid ${COLORS.border}`,
    padding: 20, marginTop: 16,
  },
  payloadGrid: {
    display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16,
  },
  codeBlock: {
    background: COLORS.bgPanel, border: `1px solid ${COLORS.border}`,
    padding: 12, fontSize: 11, fontFamily: "'JetBrains Mono', monospace",
    color: COLORS.textMuted, overflow: 'auto', maxHeight: 280,
    lineHeight: 1.5, whiteSpace: 'pre',
  },
  codeTitle: {
    fontSize: 12, fontWeight: 600, marginBottom: 8,
    display: 'flex', alignItems: 'center', gap: 8,
  },
  highlight: {
    background: COLORS.blue + '22', padding: '0 4px', borderRadius: 2,
    color: COLORS.blue, fontSize: 10, fontWeight: 600,
  },
}

const AGENT_COLORS = { growth: COLORS.growth, risk: COLORS.risk, macro: COLORS.macro }

function RegimePerformanceTable({ data }) {
  const perf = data.summary?.agent_regime_performance || {}
  const rows = ['growth', 'risk', 'macro', 'benchmark']

  const cellColor = (val, row) => {
    if (row === 'benchmark') return COLORS.textMuted
    return val > 0 ? COLORS.green : val < 0 ? COLORS.red : COLORS.text
  }

  return (
    <div style={styles.panel}>
      <div style={styles.panelTitle}>Regime Performance</div>
      <table style={styles.table}>
        <thead>
          <tr>
            <th style={styles.th}>Agent</th>
            <th style={{ ...styles.th, textAlign: 'right' }}>Bull</th>
            <th style={{ ...styles.th, textAlign: 'right' }}>Stress</th>
            <th style={{ ...styles.th, textAlign: 'right' }}>Full</th>
            <th style={{ ...styles.th, textAlign: 'right' }}>Active</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(id => {
            const p = perf[id] || {}
            return (
              <tr key={id}>
                <td style={{
                  ...styles.td,
                  color: id === 'benchmark' ? COLORS.textMuted : AGENT_COLORS[id],
                  fontWeight: 600, textTransform: 'capitalize',
                }}>
                  {id}
                </td>
                <td style={{ ...styles.td, textAlign: 'right', color: cellColor(p.bull_return, id) }}>
                  {formatPct(p.bull_return)}
                </td>
                <td style={{ ...styles.td, textAlign: 'right', color: cellColor(p.stress_return, id) }}>
                  {formatPct(p.stress_return)}
                </td>
                <td style={{ ...styles.td, textAlign: 'right', color: cellColor(p.full_return, id) }}>
                  {formatPct(p.full_return)}
                </td>
                <td style={{ ...styles.td, textAlign: 'right', color: COLORS.text }}>
                  {p.weeks_active || 0}w
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function GovernanceTimeline({ data }) {
  const timeline = data.timeline || []
  const totalWeeks = timeline.length

  const agents = ['growth', 'risk', 'macro']

  return (
    <div style={styles.panel}>
      <div style={styles.panelTitle}>Governance Actions Timeline</div>
      {agents.map(id => {
        const segments = []
        let currentStatus = 'active'
        let segStart = 0

        timeline.forEach((w, i) => {
          const status = w.agents[id].status
          if (status !== currentStatus || i === timeline.length - 1) {
            segments.push({
              start: segStart,
              end: i,
              status: currentStatus,
            })
            currentStatus = status
            segStart = i
          }
        })

        return (
          <div key={id} style={styles.timelineRow}>
            <div style={{ ...styles.timelineLabel, color: AGENT_COLORS[id] }}>
              {id}
            </div>
            <div style={styles.timelineBar}>
              {segments.map((seg, i) => {
                const width = ((seg.end - seg.start) / totalWeeks) * 100
                const color = seg.status === 'suppressed' ? COLORS.red
                  : seg.status === 'probation' ? COLORS.amber : COLORS.green
                return (
                  <div key={i} style={{
                    width: `${width}%`, height: '100%',
                    background: color + (seg.status === 'active' ? '66' : 'cc'),
                  }} />
                )
              })}
            </div>
          </div>
        )
      })}
      <div style={{
        display: 'flex', gap: 12, marginTop: 8,
        fontSize: 10, color: COLORS.textMuted,
      }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <div style={{ width: 8, height: 8, background: COLORS.green + '66' }} /> Active
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <div style={{ width: 8, height: 8, background: COLORS.amber + 'cc' }} /> Probation
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <div style={{ width: 8, height: 8, background: COLORS.red + 'cc' }} /> Suppressed
        </span>
      </div>
    </div>
  )
}

function AttributionChart({ data }) {
  const attr = data.summary?.attribution || {}
  const chartData = [
    { name: 'Growth\nSuppression', value: Math.abs(attr.suppression_of_growth || 0), fill: COLORS.red },
    { name: 'Risk\nElevation', value: Math.abs(attr.elevation_of_risk || 0), fill: COLORS.blue },
    { name: 'Threshold\nMutation', value: Math.abs(attr.threshold_mutation || 0), fill: COLORS.purple },
  ]

  return (
    <div style={styles.panel}>
      <div style={styles.panelTitle}>Outperformance Attribution</div>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 80, right: 20 }}>
          <XAxis
            type="number" stroke={COLORS.textDim} fontSize={10}
            tickFormatter={v => formatDollar(v)}
          />
          <YAxis
            type="category" dataKey="name" stroke={COLORS.textDim}
            fontSize={10} width={75}
          />
          <Bar dataKey="value" radius={[0, 3, 3, 0]}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function PayloadComparison({ data }) {
  const payloads = data.summary?.payload_comparison || {}
  const lending = payloads.lending
  const finance = payloads.finance

  if (!lending || !finance) return null

  return (
    <div style={styles.payloadPanel}>
      <div style={{
        ...styles.panelTitle, fontSize: 15, marginBottom: 4,
      }}>
        Domain-Agnostic Payload Structure
      </div>
      <div style={{
        fontSize: 12, color: COLORS.textMuted, marginBottom: 16,
      }}>
        The governance kernel does not change. Only the domain-specific metadata
        changes. Structurally identical payloads across lending, fraud, healthcare,
        and finance.
      </div>
      <div style={styles.payloadGrid}>
        <div>
          <div style={styles.codeTitle}>
            <span>Lending Demo</span>
            <span style={styles.highlight}>PRIOR DEMO</span>
          </div>
          <div style={styles.codeBlock}>
            {JSON.stringify(lending, null, 2)}
          </div>
        </div>
        <div>
          <div style={styles.codeTitle}>
            <span>Finance Demo</span>
            <span style={{ ...styles.highlight, background: COLORS.green + '22', color: COLORS.green }}>
              THIS DEMO
            </span>
          </div>
          <div style={styles.codeBlock}>
            {JSON.stringify(finance, null, 2)}
          </div>
        </div>
      </div>
      <div style={{
        marginTop: 12, padding: '10px 14px',
        background: COLORS.blue + '11', border: `1px solid ${COLORS.blue}33`,
        fontSize: 12, color: COLORS.blueLight,
      }}>
        Same primitives: <code>Task</code>, <code>ExecutionResult</code>,
        trust scoring, suppression/redemption, threshold mutation.
        The governance layer is domain-independent.
      </div>
    </div>
  )
}

export default function ComparativeAnalytics({ data, sim }) {
  return (
    <div>
      <div style={styles.grid}>
        <RegimePerformanceTable data={data} />
        <GovernanceTimeline data={data} />
        <AttributionChart data={data} />
      </div>
      <PayloadComparison data={data} />
    </div>
  )
}
