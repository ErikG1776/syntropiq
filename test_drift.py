"""
Drift Detection Test - Forces Claim 4 to Trigger

Creates a large trust drop across two cycles to trigger drift detection.
"""

from syntropiq.core.models import Task, Agent
from syntropiq.governance.loop import GovernanceLoop
from syntropiq.persistence.state_manager import PersistentStateManager
from syntropiq.persistence.agent_registry import AgentRegistry
from syntropiq.execution.function_executor import FunctionExecutor
import time


def create_drift_executor():
    """Create executor that causes multiple consecutive failures."""
    executor = FunctionExecutor()
    
    cycle_count = {"count": 0}
    
    def drift_agent(task):
        """Agent that succeeds, then fails for 3 cycles, then recovers."""
        time.sleep(0.01)
        cycle = cycle_count["count"]
        
        # Cycle 1: Success
        # Cycles 2-4: FAIL (3 cycles of failures = 3 × 0.05 = 0.15 total drop)
        # Cycle 5+: Recover
        if cycle == 1:
            return {"result": "success"}
        elif 2 <= cycle <= 4:
            raise Exception(f"Consecutive failure in cycle {cycle}")
        else:
            return {"result": "recovered"}
    
    executor.register_function("DriftAgent", drift_agent)
    
    return executor, cycle_count


def main():
    print("\n" + "="*80)
    print("🧪 DRIFT DETECTION TEST - CLAIM 4")
    print("="*80)
    
    # Initialize
    print("\n📦 Initializing components...")
    state_manager = PersistentStateManager("test_drift.db")
    agent_registry = AgentRegistry(state_manager)
    governance_loop = GovernanceLoop(state_manager, trust_threshold=0.4)
    executor, cycle_count = create_drift_executor()
    
    # Register agent at HIGH trust
    print("\n👥 Registering agent...")
    agent_registry.register_agent("DriftAgent", ["test"], initial_trust_score=0.85)
    
    print("\n🎯 TEST SCENARIO:")
    print("   • DriftAgent starts at 0.85 (high trust)")
    print("   • Cycle 1: Succeeds → trust = 0.87")
    print("   • Cycle 2: FAILS → trust = 0.82 (Δ -0.05)")
    print("   • Cycle 3: FAILS → trust = 0.77 (Δ -0.05, cumulative = -0.10)")
    print("   • This should trigger DRIFT DETECTION (cumulative drop >= 0.1)")
    
    # Run 5 cycles
    print("\n" + "="*80)
    print("🔄 RUNNING 5 GOVERNANCE CYCLES")
    print("="*80)
    
    prev_trust = 0.85
    
    for cycle in range(1, 6):
        cycle_count["count"] = cycle
        
        print(f"\n{'='*80}")
        print(f"CYCLE {cycle}/5")
        print(f"{'='*80}")
        
        # Create tasks
        tasks = [Task(id=f"task_{i}", impact=0.8, urgency=0.7, risk=0.5, metadata={}) for i in range(3)]
        
        # Get agents
        agents = agent_registry.get_agents_dict(status="active")
        
        if not agents:
            print("\n⚠️  No active agents (all suppressed)")
            break
        
        # Show current trust
        print(f"\n📊 Trust Score BEFORE Cycle {cycle}:")
        for agent_id, agent in agents.items():
            print(f"   {agent_id}: {agent.trust_score:.3f}")
            prev_trust = agent.trust_score
        
        try:
            # Execute cycle
            result = governance_loop.execute_cycle(
                tasks=tasks,
                agents=agents,
                executor=executor,
                run_id=f"CYCLE_{cycle}"
            )
            
            # Sync trust scores
            agent_registry.sync_trust_scores()
            
            # Show results
            print(f"\n📊 CYCLE {cycle} RESULTS:")
            print(f"   Success: {result['statistics']['successes']}")
            print(f"   Failures: {result['statistics']['failures']}")
            print(f"\n   Trust Updates:")
            for agent_id, score in result['trust_updates'].items():
                delta = score - prev_trust
                arrow = "📈" if delta > 0 else "📉" if delta < 0 else "➡️"
                
                # Check for drift
                drift_status = ""
                if abs(delta) >= 0.1:
                    drift_status = f" ⚠️ DRIFT DETECTED! (|{delta:.3f}| >= 0.1)"
                
                print(f"      {arrow} {agent_id}: {prev_trust:.3f} → {score:.3f} (Δ {delta:+.3f}){drift_status}")
                prev_trust = score
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
    
    # Final analysis
    print("\n" + "="*80)
    print("📈 DRIFT ANALYSIS")
    print("="*80)
    
    drift_status = governance_loop.get_agent_status("DriftAgent")
    print(f"\n👤 DriftAgent:")
    print(f"   Trust History: {drift_status['trust_history']}")
    print(f"   Drift Detected: {drift_status['is_drifting']}")
    
    # Verify drift
    history = drift_status['trust_history']
    drift_found = False
    
    for i in range(1, len(history)):
        delta = history[i] - history[i-1]
        if abs(delta) >= 0.1:
            drift_found = True
            print(f"\n✅ CLAIM 4 (Drift Detection): VERIFIED!")
            print(f"   Trust dropped from {history[i-1]:.3f} to {history[i]:.3f}")
            print(f"   Delta: {delta:.3f} (exceeds threshold of 0.1)")
            break
    
    if not drift_found:
        # Check cumulative drop
        if len(history) >= 2:
            total_drop = history[-1] - history[0]
            print(f"\n   Total trust change: {history[0]:.3f} → {history[-1]:.3f} (Δ {total_drop:.3f})")
            if total_drop <= -0.1:
                print(f"   ⚠️  Cumulative drift of {total_drop:.3f} occurred, but cycle-to-cycle delta < 0.1")
                print(f"   Drift detection monitors cycle-to-cycle changes, not cumulative")
    
    print("\n🎉 Test Complete!\n")
    
    # Cleanup
    state_manager.close()


if __name__ == "__main__":
    main()