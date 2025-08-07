from typing import List, Dict, Any, Optional
from .battle_context import BattleContext
from .processor_pipeline import ProcessorPipeline
from .battle_simulator import BattleEvent
from .game_state import GameState
from .ai_policy import HeuristicAI
from .atb_system import ATBClock
import random


class BattleEngine:
    """
    The new modular battle engine that replaces the monolithic BattleSimulator.
    Uses a processor pipeline to handle battle steps in a modular, extensible way.
    """
    
    def __init__(self, game_state: GameState, ai: HeuristicAI, clock: ATBClock, rng: random.Random):
        """
        Initialize the battle engine with core dependencies.
        
        Args:
            game_state: The current game state containing characters and battle info
            ai: The AI interface for making decisions
            clock: The ATB clock for timing
            rng: Random number generator for deterministic randomness
        """
        self.game_state = game_state
        self.ai = ai
        self.clock = clock
        self.rng = rng
        
        # Initialize the processor pipeline
        self.pipeline = ProcessorPipeline()
        
        # Battle state
        self.events: List[BattleEvent] = []
        self.step_count = 0
        self.battle_finished = False
        
        # Validate pipeline configuration
        issues = self.pipeline.validate_pipeline()
        if issues:
            raise ValueError(f"Invalid pipeline configuration: {issues}")
    
    def step(self) -> List[BattleEvent]:
        """
        Execute a single battle step using the processor pipeline.
        
        Returns:
            List[BattleEvent]: Events generated during this step
        """
        if self.battle_finished:
            return []
        
        # Create battle context for this step
        context = BattleContext(
            state=self.game_state,
            ai=self.ai,
            clock=self.clock,
            rng=self.rng
        )
        
        context.log(f"Starting battle step {self.step_count + 1}")
        
        # Execute the processor pipeline
        success = self.pipeline.execute_step(context)
        
        if not success:
            context.log("Battle step failed - battle may be in invalid state")
            # Could potentially mark battle as finished or handle error
        
        # Collect events from this step
        step_events = context.events.copy()
        self.events.extend(step_events)
        
        # Increment step counter
        self.step_count += 1
        
        # Check if battle is finished
        self._check_battle_completion()
        
        context.log(f"Battle step {self.step_count} completed with {len(step_events)} events")
        
        return step_events
    
    def run_to_completion(self, max_steps: int = 1000) -> List[BattleEvent]:
        """
        Run the battle to completion or until max_steps is reached.
        
        Args:
            max_steps: Maximum number of steps to prevent infinite loops
            
        Returns:
            List[BattleEvent]: All events generated during the battle
        """
        all_events = []
        steps_taken = 0
        
        while not self.battle_finished and steps_taken < max_steps:
            step_events = self.step()
            all_events.extend(step_events)
            steps_taken += 1
        
        if steps_taken >= max_steps:
            print(f"Warning: Battle stopped after {max_steps} steps to prevent infinite loop")
        
        return all_events
    
    def _check_battle_completion(self) -> None:
        """Check if the battle has finished (all characters in a team are defeated)"""
        # Get characters by faction
        team1_chars = [c for c in self.game_state.all_characters() if c.faction == "team_1"]
        team2_chars = [c for c in self.game_state.all_characters() if c.faction == "team_2"]
        
        team1_alive = any(char.hp > 0 for char in team1_chars)
        team2_alive = any(char.hp > 0 for char in team2_chars)
        
        if not team1_alive or not team2_alive:
            self.battle_finished = True
    
    def is_battle_finished(self) -> bool:
        """Check if the battle has finished"""
        return self.battle_finished
    
    def get_battle_events(self) -> List[BattleEvent]:
        """Get all battle events generated so far"""
        return self.events.copy()
    
    def get_step_count(self) -> int:
        """Get the number of steps executed"""
        return self.step_count
    
    def get_pipeline_info(self) -> dict:
        """Get information about the processor pipeline"""
        return self.pipeline.get_pipeline_info()
    
    def add_processor(self, processor, position: Optional[int] = None) -> None:
        """Add a custom processor to the pipeline"""
        self.pipeline.add_processor(processor, position)
    
    def remove_processor(self, processor_name: str) -> bool:
        """Remove a processor from the pipeline"""
        return self.pipeline.remove_processor(processor_name)
    
    def get_processor(self, processor_name: str):
        """Get a processor by name"""
        return self.pipeline.get_processor(processor_name)
    
    def create_actor_views(self) -> Dict[str, Any]:
        """
        Create actor views for AI decision making.
        This maintains compatibility with the existing AI interface.
        
        Returns:
            Dict[str, Any]: Actor views for each character
        """
        views = {}
        
        for char in self.game_state.all_characters():
            if char.hp > 0:  # Only include living characters
                views[char.id] = {
                    'id': char.id,
                    'hp': char.hp,
                    'qi': char.qi,
                    'stats': char.stats,
                    'skills': char.skills,
                    'time_units': getattr(char, 'time_units', 0)
                }
        
        return views
    
    def map_event_for_narration(self, event: BattleEvent) -> Dict[str, Any]:
        """
        Map a battle event to a context dictionary for narration.
        This maintains compatibility with the existing narration system.
        
        Args:
            event: The battle event to map
            
        Returns:
            Dict[str, Any]: Context dictionary for narration
        """
        context = {
            'event_type': event.event_type,
            'actor_id': event.actor,
            'target_id': event.target,
            'skill_id': event.skill_id,
            'skill_tier': event.skill_tier,
            'outcome': event.outcome,
            'damage': event.damage,
            'damage_percent': event.damage_percent,
            'remaining_hp_percent': event.remaining_hp_percent,
            'qi_cost': event.qi_cost,
            'cooldown_remaining': event.cooldown_remaining,
            'timestamp': event.timestamp
        }
        
        # Add character information
        actor = self._find_character(event.actor)
        if actor:
            context['actor_name'] = getattr(actor, 'name', actor.id)
        
        target = self._find_character(event.target)
        if target:
            context['target_name'] = getattr(target, 'name', target.id)
        
        # Add skill information if available
        if hasattr(self.ai, 'skills_db') and event.skill_id:
            try:
                skill_name = self.ai.skills_db.get_skill_name(event.skill_id)
                context['skill_name'] = skill_name
                context['skill_name_chinese'] = skill_name  # Assuming Chinese names
            except Exception:
                context['skill_name'] = event.skill_id
                context['skill_name_chinese'] = event.skill_id
        
        # Add Chinese labels for event types
        event_type_labels = {
            'attack': '攻击',
            'defend': '防御',
            'dodge': '闪避',
            'critical': '暴击',
            'miss': '未命中',
            'defeat': '击败'
        }
        context['event_type_chinese'] = event_type_labels.get(event.event_type, event.event_type)
        
        return context
    
    def _find_character(self, character_id: str):
        """Find a character by ID in the game state"""
        for char in self.game_state.all_characters():
            if char.id == character_id:
                return char
        return None
    
    def reset(self) -> None:
        """Reset the battle engine for a new battle"""
        self.events.clear()
        self.step_count = 0
        self.battle_finished = False
        self.clock.reset() if hasattr(self.clock, 'reset') else None