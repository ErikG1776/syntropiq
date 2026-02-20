import React from 'react'
import {
  ComposedChart, Line, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from 'recharts'
import { COLORS } from '../utils/colors'
import { formatDollarFull, formatDate } from '../utils/formatters'

const REGIME_SHIFT_WEEK = 53

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  const outperf = (d?.portfolio || 0) - (d?.benchmark || 0)
  return (
    <div style={{
      background: COLORS.bgCard, border: `1px solid ${COLORS.border}`,
      padding: '10px 14px', fontSize: 12,
    }}>
      <div style={{ fontWeight: 600, marginBottom: 6 }}>
        Week {d?.week} — {formatDate(d?.date)}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 24, marginBottom: 2 }}>
        <span style={{ color: COLORS.blue }}>Governed</span>
        <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>
          {formatDollarFull(d?.portfolio)}
        </span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 24, marginBottom: 2 }}>
        <span style={{ color: COLORS.textMuted }}>Benchmark</span>
        <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>
          {formatDollarFull(d?.benchmark)}
        </span>
      </div>
      <div style={{
        borderTop: `1px solid ${COLORS.border}`, paddingTop: 4, marginTop: 4,
        display: 'flex', justifyContent: 'space-between', gap: 24,
      }}>
        <span>Outperformance</span>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          color: outperf >= 0 ? COLORS.green : COLORS.red,
          fontWeight: 600,
        }}>
          {outperf >= 0 ? '+' : ''}{formatDollarFull(outperf)}
        </span>
      </div>
    </div>
  )
}

export default function PortfolioPerformanceChart({ sim }) {
  const { visibleTimeline } = sim

  const chartData = visibleTimeline.map(w => ({
    week: w.week,
    date: w.date,
    portfolio: w.portfolio_value,
    benchmark: w.benchmark_value,
    spread: w.portfolio_value - w.benchmark_value,
  }))

  const allValues = chartData.flatMap(d => [d.portfolio, d.benchmark])
  const minVal = allValues.length > 0
    ? Math.floor(Math.min(...allValues) / 100000) * 100000 : 9500000
  const maxVal = allValues.length > 0
    ? Math.ceil(Math.max(...allValues) / 100000) * 100000 : 13000000

  return (
    <div style={{
      background: COLORS.bgCard, border: `1px solid ${COLORS.border}`,
      padding: '20px 16px 8px 0',
    }}>
      <ResponsiveContainer width="100%" height={350}>
        <ComposedChart data={chartData} margin={{ top: 10, right: 20, bottom: 0, left: 20 }}>
          <defs>
            <linearGradient id="spreadGreen" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={COLORS.green} stopOpacity={0.2} />
              <stop offset="100%" stopColor={COLORS.green} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="week" stroke={COLORS.textDim} fontSize={11}
            tickFormatter={v => v % 10 === 0 ? `W${v}` : ''}
          />
          <YAxis
            stroke={COLORS.textDim} fontSize={11}
            domain={[minVal, maxVal]}
            tickFormatter={v => `$${(v / 1e6).toFixed(1)}M`}
          />
          <Tooltip content={<CustomTooltip />} />

          {sim.currentWeek >= REGIME_SHIFT_WEEK && (
            <ReferenceLine
              x={REGIME_SHIFT_WEEK}
              stroke={COLORS.purple} strokeDasharray="6 4" strokeWidth={2}
            />
          )}

          <ReferenceLine
            y={10000000} stroke={COLORS.textDim}
            strokeDasharray="4 4" strokeWidth={1}
          />

          <Line
            type="monotone" dataKey="benchmark" stroke={COLORS.textDim}
            strokeWidth={2} strokeDasharray="6 4" dot={false}
            animationDuration={300}
          />
          <Line
            type="monotone" dataKey="portfolio" stroke={COLORS.blue}
            strokeWidth={2.5} dot={false} animationDuration={300}
          />
        </ComposedChart>
      </ResponsiveContainer>
      <div style={{
        display: 'flex', justifyContent: 'center', gap: 24,
        padding: '8px 0', fontSize: 12, color: COLORS.textMuted,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 20, height: 2, background: COLORS.blue }} />
          Syntropiq Governed
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{
            width: 20, height: 2, background: COLORS.textDim,
            borderTop: '2px dashed ' + COLORS.textDim,
          }} />
          Passive Benchmark (60/40)
        </div>
      </div>
    </div>
  )
}
