from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from .battle_simulator import BattleEvent


@dataclass
class BattleContext:
    """
    Central data container for battle processing pipeline.
    Holds all state and data needed by processors during a battle step.
    """
    # Core battle state
    state: Any  # GameState instance
    ai: Any     # AI policy instance
    clock: Any  # ATB clock instance
    rng: Any    # Random number generator
    
    # Current step data
    current_actor_id: Optional[str] = None
    current_target_id: Optional[str] = None
    current_skill_id: Optional[str] = None
    current_skill_tier: Optional[int] = None
    
    # Processing results
    events: List[BattleEvent] = field(default_factory=list)
    step_completed: bool = False
    should_skip_remaining: bool = False
    
    # Intermediate calculations
    damage_amount: int = 0
    outcome: str = "hit"
    damage_bucket: str = "low"
    hit_result: str = "hit"
    
    # Processing metadata
    processing_log: List[str] = field(default_factory=list)
    error_occurred: bool = False
    error_message: str = ""
    
    def log(self, message: str) -> None:
        """Add a processing log entry"""
        self.processing_log.append(message)
    
    def set_error(self, message: str) -> None:
        """Mark an error occurred during processing"""
        self.error_occurred = True
        self.error_message = message
        self.log(f"ERROR: {message}")
    
    def skip_remaining_processors(self) -> None:
        """Signal that remaining processors should be skipped"""
        self.should_skip_remaining = True
        self.log("Skipping remaining processors")
    
    def add_event(self, event: BattleEvent) -> None:
        """Add a battle event to the results"""
        self.events.append(event)
        self.log(f"Added event: {event.event_type} by {event.actor}")
    
    def get_current_actor(self):
        """Get the current actor from state"""
        if self.current_actor_id:
            return self.state.get_actor(self.current_actor_id)
        return None
    
    def get_current_target(self):
        """Get the current target from state"""
        if self.current_target_id:
            return self.state.get_actor(self.current_target_id)
        return None
    
    def get_skills_db(self):
        """Get the skills database from AI"""
        return getattr(self.ai, "_skills", None)