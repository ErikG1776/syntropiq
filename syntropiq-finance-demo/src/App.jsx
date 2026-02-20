import React, { useState, useEffect } from 'react'
import { useSimulation } from './hooks/useSimulation'
import { COLORS } from './utils/colors'
import Header from './components/Header'
import HeroMetrics from './components/HeroMetrics'
import AuthorityWeightChart from './components/AuthorityWeightChart'
import TrustScoreChart from './components/TrustScoreChart'
import PortfolioPerformanceChart from './components/PortfolioPerformanceChart'
import AgentStatusPanel from './components/AgentStatusPanel'
import EventStream from './components/EventStream'
import ComparativeAnalytics from './components/ComparativeAnalytics'
import PlaybackControls from './components/PlaybackControls'
import simulationData from '../data/simulation_data.json'

const styles = {
  app: {
    background: COLORS.bg,
    color: COLORS.text,
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    minHeight: '100vh',
    paddingBottom: 80,
  },
  intro: {
    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
    background: COLORS.bg,
    display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center',
    zIndex: 9999,
    transition: 'opacity 0.8s ease',
  },
  introLogo: {
    fontSize: 48, fontWeight: 700, color: COLORS.blue,
    letterSpacing: '-1px', marginBottom: 16,
  },
  introTagline: {
    fontSize: 18, color: COLORS.textMuted, fontWeight: 400,
    letterSpacing: '0.5px',
  },
  regimeFlash: {
    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
    background: 'rgba(168, 85, 247, 0.15)',
    display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center',
    zIndex: 8888, pointerEvents: 'none',
  },
  regimeFlashText: {
    fontSize: 36, fontWeight: 700, color: COLORS.purple,
    letterSpacing: '2px', textTransform: 'uppercase',
  },
  regimeFlashSub: {
    fontSize: 18, color: COLORS.purpleLight, marginTop: 8,
  },
  content: {
    maxWidth: 1400, margin: '0 auto', padding: '0 24px',
  },
  section: {
    marginTop: 32,
  },
  sectionTitle: {
    fontSize: 14, fontWeight: 600, color: COLORS.textMuted,
    textTransform: 'uppercase', letterSpacing: '1.5px',
    marginBottom: 16,
  },
}

export default function App() {
  const sim = useSimulation(simulationData)
  const [showIntro, setShowIntro] = useState(true)
  const [introFading, setIntroFading] = useState(false)
  const [showRegimeFlash, setShowRegimeFlash] = useState(false)
  const [prevWeek, setPrevWeek] = useState(0)

  // Intro screen timer
  useEffect(() => {
    const t1 = setTimeout(() => setIntroFading(true), 2200)
    const t2 = setTimeout(() => { setShowIntro(false); sim.setIntroComplete(true) }, 3000)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [])

  // Regime shift flash
  useEffect(() => {
    const regimeWeek = simulationData?.summary?.regime_shift_week || 53
    if (sim.currentWeek === regimeWeek && prevWeek === regimeWeek - 1) {
      setShowRegimeFlash(true)
      setTimeout(() => setShowRegimeFlash(false), 2000)
    }
    setPrevWeek(sim.currentWeek)
  }, [sim.currentWeek])

  if (showIntro) {
    return (
      <div style={{ ...styles.intro, opacity: introFading ? 0 : 1 }}>
        <div style={styles.introLogo}>SYNTROPIQ</div>
        <div style={styles.introTagline}>
          The Governance Layer for Autonomous Decision Systems
        </div>
      </div>
    )
  }

  return (
    <div style={styles.app}>
      {showRegimeFlash && (
        <div style={styles.regimeFlash}>
          <div style={styles.regimeFlashText}>Regime Shift</div>
          <div style={styles.regimeFlashSub}>Stress Phase Begins — January 2022</div>
        </div>
      )}

      <Header sim={sim} summary={simulationData.summary} />

      <div style={styles.content}>
        <div style={{ marginTop: 88 }}>
          <HeroMetrics sim={sim} summary={simulationData.summary} />
        </div>

        <div style={styles.section}>
          <div style={styles.sectionTitle}>Authority Weight Over Time</div>
          <AuthorityWeightChart sim={sim} />
        </div>

        <div style={styles.section}>
          <div style={styles.sectionTitle}>Trust Score Trajectories</div>
          <TrustScoreChart sim={sim} />
        </div>

        <div style={styles.section}>
          <div style={styles.sectionTitle}>Portfolio Performance vs Benchmark</div>
          <PortfolioPerformanceChart sim={sim} />
        </div>

        <div style={styles.section}>
          <div style={styles.sectionTitle}>Agent Status</div>
          <AgentStatusPanel sim={sim} />
        </div>

        <div style={styles.section}>
          <div style={styles.sectionTitle}>Governance Event Stream</div>
          <EventStream sim={sim} />
        </div>

        <div style={styles.section}>
          <div style={styles.sectionTitle}>Comparative Analytics</div>
          <ComparativeAnalytics data={simulationData} sim={sim} />
        </div>
      </div>

      <PlaybackControls sim={sim} />
    </div>
  )
}
