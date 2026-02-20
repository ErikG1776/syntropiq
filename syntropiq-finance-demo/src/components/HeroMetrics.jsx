import React from 'react'
import { COLORS } from '../utils/colors'
import { formatDollarFull, formatDollar, formatPct } from '../utils/formatters'

const styles = {
  row: {
    display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16,
  },
  card: {
    background: COLORS.bgCard, border: `1px solid ${COLORS.border}`,
    padding: '20px 24px',
  },
  label: {
    fontSize: 11, color: COLORS.textMuted, fontWeight: 600,
    textTransform: 'uppercase', letterSpacing: '1px', marginBottom: 8,
  },
  value: {
    fontSize: 28, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace",
    lineHeight: 1.2,
  },
  sub: {
    fontSize: 12, color: COLORS.textMuted, marginTop: 4,
  },
}

export default function HeroMetrics({ sim, summary }) {
  const { currentData, governanceEventCount } = sim

  const portfolioValue = currentData?.portfolio_value ?? summary.starting_portfolio
  const benchmarkValue = currentData?.benchmark_value ?? summary.starting_portfolio
  const outperf = portfolioValue - benchmarkValue
  const outperfPct = benchmarkValue > 0
    ? ((portfolioValue / benchmarkValue - 1) * 100) : 0

  const ddGov = currentData?.max_drawdown_portfolio ?? 0
  const ddBm = currentData?.max_drawdown_benchmark ?? 0
  const ddReduction = ddBm !== 0
    ? Math.round((1 - ddGov / ddBm) * 100) : 0

  return (
    <div style={styles.row}>
      <div style={styles.card}>
        <div style={styles.label}>Portfolio Value</div>
        <div style={{ ...styles.value, color: COLORS.text }}>
          {formatDollarFull(portfolioValue)}
        </div>
        <div style={styles.sub}>
          Starting: {formatDollarFull(summary.starting_portfolio)}
        </div>
      </div>

      <div style={styles.card}>
        <div style={styles.label}>vs Benchmark</div>
        <div style={{
          ...styles.value,
          color: outperf >= 0 ? COLORS.green : COLORS.red,
        }}>
          {formatDollar(outperf)} / {formatPct(outperfPct)}
        </div>
        <div style={styles.sub}>
          Benchmark: {formatDollarFull(benchmarkValue)}
        </div>
      </div>

      <div style={styles.card}>
        <div style={styles.label}>Governance Events</div>
        <div style={{ ...styles.value, color: COLORS.purple }}>
          {governanceEventCount}
        </div>
        <div style={styles.sub}>
          Total at completion: {summary.total_governance_events}
        </div>
      </div>

      <div style={styles.card}>
        <div style={styles.label}>Max Drawdown</div>
        <div style={{ ...styles.value, color: COLORS.amber }}>
          {ddReduction > 0 ? `${ddReduction}% less` : `${formatPct(ddGov * 100)}`}
        </div>
        <div style={styles.sub}>
          Governed: {formatPct(ddGov * 100)} vs Benchmark: {formatPct(ddBm * 100)}
        </div>
      </div>
    </div>
  )
}
