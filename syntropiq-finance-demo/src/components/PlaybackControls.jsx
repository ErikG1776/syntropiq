import React from 'react'
import { COLORS } from '../utils/colors'

const styles = {
  bar: {
    position: 'fixed', bottom: 0, left: 0, right: 0,
    background: 'rgba(10, 14, 26, 0.95)',
    backdropFilter: 'blur(12px)',
    borderTop: `1px solid ${COLORS.border}`,
    padding: '10px 24px',
    display: 'flex', alignItems: 'center', gap: 12,
    zIndex: 1000,
  },
  btn: {
    background: COLORS.bgCard, border: `1px solid ${COLORS.border}`,
    color: COLORS.text, padding: '6px 12px', cursor: 'pointer',
    fontSize: 13, fontWeight: 500, fontFamily: 'inherit',
    transition: 'background 0.2s',
    minWidth: 40, textAlign: 'center',
  },
  btnPrimary: {
    background: COLORS.blue, border: `1px solid ${COLORS.blue}`,
    color: '#fff', padding: '6px 16px', cursor: 'pointer',
    fontSize: 13, fontWeight: 600, fontFamily: 'inherit',
    minWidth: 60, textAlign: 'center',
  },
  speedBtn: {
    background: 'transparent', border: `1px solid ${COLORS.border}`,
    color: COLORS.textMuted, padding: '4px 8px', cursor: 'pointer',
    fontSize: 11, fontFamily: "'JetBrains Mono', monospace",
    transition: 'all 0.2s',
  },
  speedActive: {
    background: COLORS.blue + '22', border: `1px solid ${COLORS.blue}`,
    color: COLORS.blue,
  },
  scrubber: {
    flex: 1, height: 4, appearance: 'none', background: COLORS.border,
    borderRadius: 2, outline: 'none', cursor: 'pointer',
    WebkitAppearance: 'none',
  },
  label: {
    fontSize: 11, color: COLORS.textMuted, whiteSpace: 'nowrap',
  },
  jumpBtn: {
    background: 'transparent', border: `1px solid ${COLORS.purple}44`,
    color: COLORS.purple, padding: '4px 10px', cursor: 'pointer',
    fontSize: 11, fontWeight: 500, fontFamily: 'inherit',
    whiteSpace: 'nowrap',
  },
}

export default function PlaybackControls({ sim }) {
  const {
    currentWeek, totalWeeks, isPlaying, speed,
    play, pause, reset, stepForward, stepBack,
    seekTo, setSpeed, jumpToRegimeShift,
  } = sim

  return (
    <div style={styles.bar}>
      <button style={styles.btn} onClick={reset}>RESET</button>
      <button style={styles.btn} onClick={() => stepBack(10)}>-10</button>
      <button style={styles.btn} onClick={() => stepBack(1)}>-1</button>
      <button
        style={styles.btnPrimary}
        onClick={isPlaying ? pause : play}
      >
        {isPlaying ? 'PAUSE' : 'PLAY'}
      </button>
      <button style={styles.btn} onClick={() => stepForward(1)}>+1</button>
      <button style={styles.btn} onClick={() => stepForward(10)}>+10</button>

      <div style={{ display: 'flex', gap: 4, marginLeft: 8 }}>
        <span style={styles.label}>Speed:</span>
        {[1, 2, 4, 8].map(s => (
          <button key={s} onClick={() => setSpeed(s)} style={{
            ...styles.speedBtn,
            ...(speed === s ? styles.speedActive : {}),
          }}>
            {s}x
          </button>
        ))}
      </div>

      <input
        type="range"
        min={0}
        max={totalWeeks}
        value={currentWeek}
        onChange={e => seekTo(Number(e.target.value))}
        style={styles.scrubber}
      />

      <span style={{
        ...styles.label,
        fontFamily: "'JetBrains Mono', monospace",
        minWidth: 70, textAlign: 'right',
      }}>
        {currentWeek} / {totalWeeks}
      </span>

      <button style={styles.jumpBtn} onClick={jumpToRegimeShift}>
        JUMP TO REGIME SHIFT
      </button>
    </div>
  )
}
