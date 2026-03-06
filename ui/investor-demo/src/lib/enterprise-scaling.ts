import type { DomainId, CumulativeStats, DomainConfig } from "./demo-data";

interface DomainScaling {
  annualVolume: number;
  baselineRiskRate: number;
  avgLossPerEvent: number;
  volumeLabel: string;
}

const SCALING: Record<DomainId, DomainScaling> = {
  fraud: {
    annualVolume: 250_000_000,
    baselineRiskRate: 0.003,
    avgLossPerEvent: 185,
    volumeLabel: "250M transactions/yr",
  },
  lending: {
    annualVolume: 48_000,
    baselineRiskRate: 0.022,
    avgLossPerEvent: 32_000,
    volumeLabel: "48K originations/yr",
  },
  readmission: {
    annualVolume: 18_000,
    baselineRiskRate: 0.148,
    avgLossPerEvent: 15_200,
    volumeLabel: "18K discharges/yr",
  },
};

export interface EnterpriseProjection {
  annualRiskExposure: number;
  withoutGovernance: number;
  withSyntropiq: number;
  reductionPct: number;
  netAnnualSavings: number;
  volumeLabel: string;
}

export function computeEnterpriseProjection(
  stats: CumulativeStats,
  domain: DomainConfig
): EnterpriseProjection {
  const scaling = SCALING[domain.id];

  const annualRiskExposure =
    scaling.annualVolume * scaling.baselineRiskRate * scaling.avgLossPerEvent;

  // Governance reduction derived from observed demo behavior
  const observedReduction =
    stats.totalLossWithout > 0
      ? stats.lossePrevented / stats.totalLossWithout
      : 0;

  const withoutGovernance = annualRiskExposure;
  const withSyntropiq = annualRiskExposure * (1 - observedReduction);
  const netAnnualSavings = withoutGovernance - withSyntropiq;
  const reductionPct =
    withoutGovernance > 0
      ? (netAnnualSavings / withoutGovernance) * 100
      : 0;

  return {
    annualRiskExposure,
    withoutGovernance,
    withSyntropiq,
    reductionPct,
    netAnnualSavings,
    volumeLabel: scaling.volumeLabel,
  };
}
