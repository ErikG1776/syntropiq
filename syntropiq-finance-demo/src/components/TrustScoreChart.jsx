import React from 'react'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine, ReferenceArea,
} from 'recharts'
import { COLORS } from '../utils/colors'
import { formatDate, formatTrust } from '../utils/formatters'

const SUPPRESSION_THRESHOLD = 0.40
const PROBATION_THRESHOLD = 0.55
const REGIME_SHIFT_WEEK = 53

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  return (
    <div style={{
      background: COLORS.bgCard, border: `1px solid ${COLORS.border}`,
      padding: '10px 14px', fontSize: 12,
    }}>
      <div style={{ fontWeight: 600, marginBottom: 6 }}>
        Week {d?.week} — {formatDate(d?.date)}
      </div>
      {['growth', 'risk', 'macro'].map(id => (
        <div key={id} style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 2 }}>
          <span style={{ color: COLORS[id], textTransform: 'capitalize' }}>{id}</span>
          <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>
            {formatTrust(d?.[id] ?? 0)}
          </span>
          <span style={{
            fontSize: 10,
            color: d?.[`${id}_status`] === 'suppressed' ? COLORS.red
              : d?.[`${id}_status`] === 'probation' ? COLORS.amber : COLORS.green,
            textTransform: 'uppercase',
          }}>
            {d?.[`${id}_status`] || ''}
          </span>
        </div>
      ))}
    </div>
  )
}

export default function TrustScoreChart({ sim }) {
  const { visibleTimeline } = sim

  const chartData = visibleTimeline.map(w => ({
    week: w.week,
    date: w.date,
    growth: w.agents.growth.trust,
    risk: w.agents.risk.trust,
    macro: w.agents.macro.trust,
    growth_status: w.agents.growth.status,
    risk_status: w.agents.risk.status,
    macro_status: w.agents.macro.status,
  }))

  return (
    <div style={{
      background: COLORS.bgCard, border: `1px solid ${COLORS.border}`,
      padding: '20px 16px 8px 0',
    }}>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData} margin={{ top: 10, right: 20, bottom: 0, left: 20 }}>
          <XAxis
            dataKey="week" stroke={COLORS.textDim} fontSize={11}
            tickFormatter={v => v % 10 === 0 ? `W${v}` : ''}
          />
          <YAxis
            stroke={COLORS.textDim} fontSize={11}
            domain={[0, 1]}
            tickFormatter={v => v.toFixed(1)}
          />
          <Tooltip content={<CustomTooltip />} />

          <ReferenceLine
            y={SUPPRESSION_THRESHOLD}
            stroke={COLORS.red} strokeDasharray="6 4" strokeWidth={1}
            label={{ value: 'Suppression', position: 'right', fill: COLORS.red, fontSize: 10 }}
          />
          <ReferenceLine
            y={PROBATION_THRESHOLD}
            stroke={COLORS.amber} strokeDasharray="4 4" strokeWidth={1}
            label={{ value: 'Probation', position: 'right', fill: COLORS.amber, fontSize: 10 }}
          />

          {sim.currentWeek >= REGIME_SHIFT_WEEK && (
            <ReferenceLine
              x={REGIME_SHIFT_WEEK}
              stroke={COLORS.purple} strokeDasharray="6 4" strokeWidth={2}
            />
          )}

          <Line
            type="monotone" dataKey="growth" stroke={COLORS.growth}
            strokeWidth={2} dot={false} animationDuration={300}
          />
          <Line
            type="monotone" dataKey="risk" stroke={COLORS.risk}
            strokeWidth={2} dot={false} animationDuration={300}
          />
          <Line
            type="monotone" dataKey="macro" stroke={COLORS.macro}
            strokeWidth={2} dot={false} animationDuration={300}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
