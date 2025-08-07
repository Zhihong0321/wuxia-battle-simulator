from typing import List
from ..step_processor import StepProcessor
from ..battle_context import BattleContext


class ATBProcessor(StepProcessor):
    """
    Handles ATB (Active Time Battle) clock advancement and actor selection.
    Determines which character gets to act next based on agility and time units.
    """
    
    def __init__(self):
        super().__init__("ATB Processor", critical=True)
    
    def can_process(self, context: BattleContext) -> bool:
        """Always process if battle is not over"""
        return not context.state.is_battle_over()
    
    def process(self, context: BattleContext) -> None:
        """Advance ATB clock and select next actor"""
        context.log("Processing ATB clock advancement")
        
        # Create actor views for ATB clock
        views = self._create_actor_views(context)
        
        # Advance ATB clock to select next actor
        chosen_id = context.clock.tick(views)
        
        # Sync time units back to game state
        self._sync_time_units_back(context, views)
        
        if not chosen_id:
            context.log("No actor selected by ATB clock")
            context.skip_remaining_processors()
            return
        
        # Verify selected actor is alive
        actor = context.state.get_actor(chosen_id)
        if not actor.is_alive():
            context.log(f"Selected actor {chosen_id} is not alive")
            context.skip_remaining_processors()
            return
        
        # Set current actor in context
        context.current_actor_id = chosen_id
        context.log(f"Selected actor: {chosen_id}")
        
        # Decrement cooldowns for the acting character
        context.state.decrement_cooldowns(chosen_id)
        context.log(f"Decremented cooldowns for {chosen_id}")
    
    def _create_actor_views(self, context: BattleContext) -> List:
        """Create actor views for ATB clock"""
        views = []
        for character in context.state.living():
            view = type("ActorView", (), {
                "actor_id": character.id,
                "agility": character.stats.agility,
                "time_units": character.time_units
            })()
            views.append(view)
        return views
    
    def _sync_time_units_back(self, context: BattleContext, views: List) -> None:
        """Sync time units from views back to game state"""
        for view in views:
            actor = context.state.get_actor(view.actor_id)
            actor.time_units = view.time_units