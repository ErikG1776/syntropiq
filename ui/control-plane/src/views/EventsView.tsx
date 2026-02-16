import type { ControlPlaneState } from "../types/controlPlane";
import { GovernanceEventStream } from "../components/overview/GovernanceEventStream";

interface EventsViewProps {
  state: ControlPlaneState;
}

export function EventsView({ state }: EventsViewProps) {
  return <GovernanceEventStream events={state.events} maxHeightClassName="max-h-[72vh]" title="Event Log" />;
}
