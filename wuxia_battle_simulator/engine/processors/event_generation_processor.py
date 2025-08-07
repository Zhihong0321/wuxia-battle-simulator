from ..step_processor import StepProcessor
from ..battle_context import BattleContext
from ..battle_simulator import BattleEvent


class EventGenerationProcessor(StepProcessor):
    """
    Generates the final battle events for the current step.
    Creates attack events with all calculated outcomes and damage.
    """
    
    def __init__(self):
        super().__init__("Event Generation Processor", critical=True)
    
    def can_process(self, context: BattleContext) -> bool:
        """Always generate events for completed steps"""
        return context.current_skill_id is not None
    
    def process(self, context: BattleContext) -> None:
        """Generate the main battle event for this step"""
        context.log("Generating battle events")
        
        actor = context.get_current_actor()
        target = context.get_current_target()
        skills_db = context.get_skills_db()
        
        if not actor or not skills_db:
            context.set_error("Missing required components for event generation")
            return
        
        try:
            # Get skill parameters for event details
            skill_params = skills_db.get_tier_params(context.current_skill_id, context.current_skill_tier)
            
            # Calculate remaining HP percentage for target
            remaining_hp_percent = 1.0
            if target:
                remaining_hp_percent = target.hp / target.stats.max_hp if target.stats.max_hp > 0 else 0.0
            
            # Create the main attack event
            attack_event = BattleEvent(
                timestamp=context.clock.current_time(),
                event_type="attack",
                actor=actor.id,
                target=context.current_target_id or "",
                skill_id=context.current_skill_id,
                skill_tier=context.current_skill_tier,
                outcome=context.outcome or "hit",
                damage=context.damage_amount or 0,
                damage_percent=context.damage_bucket or "low",
                remaining_hp_percent=remaining_hp_percent,
                qi_cost=skill_params.qi_cost,
                cooldown_remaining=skill_params.cooldown
            )
            
            context.add_event(attack_event)
            context.log(f"Generated attack event: {context.current_skill_id} -> {context.current_target_id}")
            
            # Generate additional events for special outcomes
            self._generate_special_outcome_events(context)
            
        except Exception as e:
            context.set_error(f"Failed to generate events: {str(e)}")
    
    def _generate_special_outcome_events(self, context: BattleContext) -> None:
        """Generate additional events for special outcomes like critical hits"""
        try:
            # Add critical hit event if applicable
            if context.outcome == "critical":
                crit_event = BattleEvent(
                    timestamp=context.clock.current_time(),
                    event_type="critical",
                    actor=context.current_actor_id or "",
                    target=context.current_target_id or "",
                    skill_id=context.current_skill_id,
                    skill_tier=context.current_skill_tier,
                    outcome="critical",
                    damage=0,
                    damage_percent="low",
                    remaining_hp_percent=1.0,
                    qi_cost=0,
                    cooldown_remaining=0
                )
                context.add_event(crit_event)
                context.log("Generated critical hit event")
            
            # Add defeat event if target was defeated
            target = context.get_current_target()
            if target and target.hp <= 0:
                defeat_event = BattleEvent(
                    timestamp=context.clock.current_time(),
                    event_type="defeat",
                    actor=context.current_target_id or "",
                    target=context.current_target_id or "",
                    skill_id="",
                    skill_tier=1,
                    outcome="defeated",
                    damage=0,
                    damage_percent="low",
                    remaining_hp_percent=0.0,
                    qi_cost=0,
                    cooldown_remaining=0
                )
                context.add_event(defeat_event)
                context.log(f"Generated defeat event for {target.id}")
        
        except Exception as e:
            context.log(f"Failed to generate special outcome events: {str(e)}")