import React from 'react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { COLORS } from '../utils/colors'
import { formatDate } from '../utils/formatters'

const REGIME_SHIFT_WEEK = 53

function CustomTooltip({ active, payload, label }) {
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
            {((d?.[id] || 0) * 100).toFixed(1)}%
          </span>
        </div>
      ))}
    </div>
  )
}

export default function AuthorityWeightChart({ sim }) {
  const { visibleTimeline } = sim

  const chartData = visibleTimeline.map(w => ({
    week: w.week,
    date: w.date,
    growth: w.agents.growth.authority_weight,
    macro: w.agents.macro.authority_weight,
    risk: w.agents.risk.authority_weight,
  }))

  return (
    <div style={{
      background: COLORS.bgCard, border: `1px solid ${COLORS.border}`,
      padding: '20px 16px 8px 0',
    }}>
      <ResponsiveContainer width="100%" height={420}>
        <AreaChart data={chartData} margin={{ top: 10, right: 20, bottom: 0, left: 20 }}>
          <defs>
            <linearGradient id="growthFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={COLORS.growth} stopOpacity={0.8} />
              <stop offset="95%" stopColor={COLORS.growth} stopOpacity={0.3} />
            </linearGradient>
            <linearGradient id="riskFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={COLORS.risk} stopOpacity={0.8} />
              <stop offset="95%" stopColor={COLORS.risk} stopOpacity={0.3} />
            </linearGradient>
            <linearGradient id="macroFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={COLORS.macro} stopOpacity={0.8} />
              <stop offset="95%" stopColor={COLORS.macro} stopOpacity={0.3} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="week" stroke={COLORS.textDim} fontSize={11}
            tickFormatter={v => v % 10 === 0 ? `W${v}` : ''}
          />
          <YAxis
            stroke={COLORS.textDim} fontSize={11}
            domain={[0, 1]}
            tickFormatter={v => `${(v * 100).toFixed(0)}%`}
          />
          <Tooltip content={<CustomTooltip />} />
          {sim.currentWeek >= REGIME_SHIFT_WEEK && (
            <ReferenceLine
              x={REGIME_SHIFT_WEEK}
              stroke={COLORS.purple}
              strokeDasharray="6 4"
              strokeWidth={2}
              label={{
                value: 'REGIME SHIFT',
                position: 'top',
                fill: COLORS.purple,
                fontSize: 11,
                fontWeight: 600,
              }}
            />
          )}
          <Area
            type="monotone" dataKey="growth" stackId="1"
            stroke={COLORS.growth} fill="url(#growthFill)"
            strokeWidth={2} animationDuration={300}
          />
          <Area
            type="monotone" dataKey="macro" stackId="1"
            stroke={COLORS.macro} fill="url(#macroFill)"
            strokeWidth={2} animationDuration={300}
          />
          <Area
            type="monotone" dataKey="risk" stackId="1"
            stroke={COLORS.risk} fill="url(#riskFill)"
            strokeWidth={2} animationDuration={300}
          />
        </AreaChart>
      </ResponsiveContainer>
      <div style={{
        display: 'flex', justifyContent: 'center', gap: 24,
        padding: '8px 0', fontSize: 12, color: COLORS.textMuted,
      }}>
        {[['Growth', COLORS.growth], ['Macro', COLORS.macro], ['Risk', COLORS.risk]].map(([n, c]) => (
          <div key={n} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 12, height: 12, background: c, borderRadius: 2 }} />
            {n} Agent
          </div>
        ))}
      </div>
    </div>
  )
}
