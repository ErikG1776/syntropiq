export function formatDollar(value) {
  if (value === null || value === undefined) return '$0'
  const abs = Math.abs(value)
  const sign = value < 0 ? '-' : value > 0 ? '+' : ''
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(2)}M`
  if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(0)}K`
  return `${sign}$${abs.toFixed(0)}`
}

export function formatDollarFull(value) {
  if (value === null || value === undefined) return '$0'
  return '$' + Math.round(value).toLocaleString()
}

export function formatPct(value, decimals = 2) {
  if (value === null || value === undefined) return '0%'
  const sign = value > 0 ? '+' : ''
  return `${sign}${(value).toFixed(decimals)}%`
}

export function formatPctRaw(value, decimals = 2) {
  if (value === null || value === undefined) return '0%'
  const sign = value > 0 ? '+' : ''
  return `${sign}${(value * 100).toFixed(decimals)}%`
}

export function formatTrust(value) {
  return value.toFixed(2)
}

export function formatWeight(value) {
  return `${(value * 100).toFixed(0)}%`
}

export function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' })
}
