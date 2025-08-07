"""Migration utilities for transitioning from BattleSimulator to BattleEngine.

This module provides utilities to help migrate existing code from the old
monolithic BattleSimulator to the new modular BattleEngine architecture.
"""

from typing import List, Dict, Any, Optional
from .battle_engine import BattleEngine
from .battle_simulator import BattleSimulator, BattleEvent
from .game_state import GameState
from .ai_policy import HeuristicAI
from .atb_system import ATBClock
import random


class BattleEngineAdapter:
    """
    Adapter class that provides a BattleSimulator-compatible interface
    while using the new BattleEngine internally.
    
    This allows existing code to work with minimal changes while
    benefiting from the new modular architecture.
    """
    
    def __init__(self, game_state: GameState, ai: HeuristicAI, clock: ATBClock, rng: random.Random):
        """Initialize the adapter with a BattleEngine instance"""
        self.engine = BattleEngine(game_state, ai, clock, rng)
        self.game_state = game_state
        self.ai = ai
        self.clock = clock
        self.rng = rng
    
    def step(self) -> List[BattleEvent]:
        """Execute a single battle step (compatible with BattleSimulator.step)"""
        return self.engine.step()
    
    def run_to_completion(self, max_steps: int = 1000) -> List[BattleEvent]:
        """Run battle to completion (compatible with BattleSimulator.run_to_completion)"""
        return self.engine.run_to_completion(max_steps)
    
    def create_actor_views(self) -> Dict[str, Any]:
        """Create actor views (compatible with BattleSimulator.create_actor_views)"""
        return self.engine.create_actor_views()
    
    def map_event_for_narration(self, event: BattleEvent) -> Dict[str, Any]:
        """Map event for narration (compatible with BattleSimulator.map_event_for_narration)"""
        return self.engine.map_event_for_narration(event)
    
    def compute_damage(self, actor, target, skill_id: str, skill_tier: int) -> tuple:
        """
        Compute damage using the new engine's damage calculation.
        
        Note: This method is deprecated in the new architecture as damage
        calculation is handled by the DamageCalculationProcessor.
        
        Returns:
            tuple: (damage_amount, outcome, damage_bucket)
        """
        # This is a compatibility method - in the new architecture,
        # damage calculation is integrated into the step processing
        print("Warning: compute_damage is deprecated. Use the processor pipeline instead.")
        
        # For compatibility, we could implement a simplified version here
        # but it's better to encourage migration to the new architecture
        return (0, "hit", "low")
    
    # Properties for compatibility
    @property
    def events(self) -> List[BattleEvent]:
        """Get all battle events (compatible with BattleSimulator.events)"""
        return self.engine.get_battle_events()
    
    @property
    def step_count(self) -> int:
        """Get step count (compatible with BattleSimulator step tracking)"""
        return self.engine.get_step_count()
    
    def is_battle_finished(self) -> bool:
        """Check if battle is finished"""
        return self.engine.is_battle_finished()


def migrate_battle_simulator_usage(old_simulator_code: str) -> str:
    """
    Provide guidance for migrating BattleSimulator code to BattleEngine.
    
    Args:
        old_simulator_code: String containing old BattleSimulator usage
        
    Returns:
        str: Suggested migration approach
    """
    migration_guide = """
    Migration Guide: BattleSimulator -> BattleEngine
    
    1. QUICK MIGRATION (Minimal Changes):
       Replace:
         from wuxia_battle_simulator.engine import BattleSimulator
         simulator = BattleSimulator(game_state, ai, clock, rng)
       
       With:
         from wuxia_battle_simulator.engine.migration import BattleEngineAdapter
         simulator = BattleEngineAdapter(game_state, ai, clock, rng)
    
    2. FULL MIGRATION (Recommended):
       Replace:
         from wuxia_battle_simulator.engine import BattleSimulator
         simulator = BattleSimulator(game_state, ai, clock, rng)
       
       With:
         from wuxia_battle_simulator.engine import BattleEngine
         engine = BattleEngine(game_state, ai, clock, rng)
    
    3. KEY DIFFERENCES:
       - BattleEngine uses a modular processor pipeline
       - Individual processors can be customized or replaced
       - Better separation of concerns and testability
       - More extensible architecture
    
    4. NEW CAPABILITIES:
       - Add custom processors: engine.add_processor(custom_processor)
       - Remove processors: engine.remove_processor("processor_name")
       - Get pipeline info: engine.get_pipeline_info()
       - Access individual processors: engine.get_processor("processor_name")
    
    5. DEPRECATED METHODS:
       - compute_damage(): Now handled by DamageCalculationProcessor
       - Direct state manipulation: Now handled by StateUpdateProcessor
    """
    
    return migration_guide


def create_battle_engine_from_simulator_config(simulator_config: Dict[str, Any]) -> BattleEngine:
    """
    Create a BattleEngine instance from BattleSimulator configuration.
    
    Args:
        simulator_config: Configuration dictionary for BattleSimulator
        
    Returns:
        BattleEngine: Configured BattleEngine instance
    """
    # Extract required components from config
    game_state = simulator_config.get('game_state')
    ai = simulator_config.get('ai')
    clock = simulator_config.get('clock')
    rng = simulator_config.get('rng')
    
    if not all([game_state, ai, clock, rng]):
        raise ValueError("Missing required components in simulator config")
    
    # Create BattleEngine
    engine = BattleEngine(game_state, ai, clock, rng)
    
    # Apply any custom configuration
    custom_processors = simulator_config.get('custom_processors', [])
    for processor in custom_processors:
        engine.add_processor(processor)
    
    return engine


def validate_migration(old_results: List[BattleEvent], new_results: List[BattleEvent]) -> Dict[str, Any]:
    """
    Validate that migration from BattleSimulator to BattleEngine produces equivalent results.
    
    Args:
        old_results: Results from BattleSimulator
        new_results: Results from BattleEngine
        
    Returns:
        Dict[str, Any]: Validation report
    """
    report = {
        'events_match': len(old_results) == len(new_results),
        'event_count_old': len(old_results),
        'event_count_new': len(new_results),
        'differences': [],
        'validation_passed': True
    }
    
    # Compare event counts
    if len(old_results) != len(new_results):
        report['differences'].append(f"Event count mismatch: {len(old_results)} vs {len(new_results)}")
        report['validation_passed'] = False
    
    # Compare individual events
    min_length = min(len(old_results), len(new_results))
    for i in range(min_length):
        old_event = old_results[i]
        new_event = new_results[i]
        
        # Compare key fields
        if old_event.event_type != new_event.event_type:
            report['differences'].append(f"Event {i}: type mismatch ({old_event.event_type} vs {new_event.event_type})")
            report['validation_passed'] = False
        
        if old_event.damage != new_event.damage:
            report['differences'].append(f"Event {i}: damage mismatch ({old_event.damage} vs {new_event.damage})")
            report['validation_passed'] = False
        
        if old_event.outcome != new_event.outcome:
            report['differences'].append(f"Event {i}: outcome mismatch ({old_event.outcome} vs {new_event.outcome})")
            report['validation_passed'] = False
    
    return report


# Convenience function for quick migration
def quick_migrate(game_state: GameState, ai: HeuristicAI, clock: ATBClock, rng: random.Random) -> BattleEngineAdapter:
    """
    Quick migration function that returns a BattleSimulator-compatible adapter.
    
    Args:
        game_state: Game state
        ai: AI interface
        clock: ATB clock
        rng: Random number generator
        
    Returns:
        BattleEngineAdapter: Adapter that works like BattleSimulator
    """
    return BattleEngineAdapter(game_state, ai, clock, rng)