import React, { useRef, useEffect } from 'react'
import { COLORS, EVENT_COLORS } from '../utils/colors'

const styles = {
  container: {
    background: COLORS.bgPanel, border: `1px solid ${COLORS.border}`,
    height: 320, overflow: 'auto', padding: 0,
    fontFamily: "'JetBrains Mono', monospace", fontSize: 12,
  },
  event: {
    padding: '6px 16px', borderLeft: '3px solid transparent',
    lineHeight: 1.5,
  },
  empty: {
    padding: 24, textAlign: 'center', color: COLORS.textDim,
    fontStyle: 'italic',
  },
}

export default function EventStream({ sim }) {
  const { visibleEvents } = sim
  const scrollRef = useRef(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [visibleEvents.length])

  // Filter to significant events (skip routine trust_increase for readability)
  const significantEvents = visibleEvents.filter(e =>
    e.type !== 'trust_increase' || e.text?.includes('0.9') || e.text?.includes('1.0')
  )

  // Show last 200 events max for performance
  const displayEvents = significantEvents.slice(-200)

  return (
    <div style={styles.container} ref={scrollRef}>
      {displayEvents.length === 0 ? (
        <div style={styles.empty}>
          Press PLAY to begin simulation...
        </div>
      ) : (
        displayEvents.map((event, i) => {
          const color = EVENT_COLORS[event.type] || COLORS.textDim
          const isRoutine = event.type === 'trust_increase'
          return (
            <div key={i} style={{
              ...styles.event,
              borderLeftColor: color,
              color: isRoutine ? COLORS.textDim : color,
              opacity: isRoutine ? 0.6 : 1,
              background: event.type === 'regime_shift'
                ? 'rgba(168, 85, 247, 0.08)'
                : event.type === 'suppression'
                ? 'rgba(239, 68, 68, 0.05)'
                : event.type === 'redemption' || event.type === 'recovery'
                ? 'rgba(34, 197, 94, 0.05)'
                : 'transparent',
            }}>
              {event.text}
            </div>
          )
        })
      )}
    </div>
  )
}
