from ..step_processor import StepProcessor
from ..battle_context import BattleContext
from ..battle_simulator import BattleEvent


class AIDecisionProcessor(StepProcessor):
    """
    Handles AI decision making for action selection.
    Determines what skill to use and which target to attack.
    """
    
    def __init__(self):
        super().__init__("AI Decision Processor", critical=False)
    
    def can_process(self, context: BattleContext) -> bool:
        """Process if we have a current actor"""
        return context.current_actor_id is not None
    
    def process(self, context: BattleContext) -> None:
        """Ask AI to choose an action"""
        context.log("Processing AI decision")
        
        actor = context.get_current_actor()
        if not actor:
            context.set_error("No current actor for AI decision")
            return
        
        try:
            # Ask AI for action
            skill_id, target_id, tier = context.ai.choose_action(context.state, actor)
            
            # Validate AI decision
            if not skill_id or tier <= 0 or not target_id:
                context.log("AI chose no action, creating defend event")
                self._create_defend_event(context, actor, target_id)
                context.skip_remaining_processors()
                return
            
            # Verify target exists
            target = context.state.get_actor(target_id)
            if not target:
                context.set_error(f"Invalid target ID: {target_id}")
                return
            
            # Store decision in context
            context.current_skill_id = skill_id
            context.current_target_id = target_id
            context.current_skill_tier = tier
            
            context.log(f"AI chose: {skill_id} (tier {tier}) targeting {target_id}")
            
        except Exception as e:
            context.log(f"AI decision failed: {str(e)}")
            # Create defend event as fallback
            self._create_defend_event(context, actor, None)
            context.skip_remaining_processors()
    
    def _create_defend_event(self, context: BattleContext, actor, target_id: str = None) -> None:
        """Create a defend/no-op event when AI cannot choose an action"""
        target = context.state.get_actor(target_id) if target_id else None
        
        defend_event = BattleEvent(
            timestamp=context.clock.current_time(),
            event_type="defend",
            actor=actor.id,
            target=target.id if target else None,
            skill_id=None,
            skill_tier=None,
            outcome="blocked",
            damage=0,
            damage_percent="low",
            remaining_hp_percent=(target.hp / target.stats.max_hp) if target else 1.0,
            qi_cost=0,
            cooldown_remaining=0
        )
        
        context.add_event(defend_event)
        context.step_completed = True