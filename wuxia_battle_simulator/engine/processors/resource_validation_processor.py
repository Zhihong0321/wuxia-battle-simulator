from ..step_processor import StepProcessor
from ..battle_context import BattleContext
from ..battle_simulator import _SkillTierParams


class ResourceValidationProcessor(StepProcessor):
    """
    Validates that the actor has sufficient resources (qi, cooldowns) to perform the chosen action.
    """
    
    def __init__(self):
        super().__init__("Resource Validation Processor", critical=False)
    
    def can_process(self, context: BattleContext) -> bool:
        """Process if we have a skill decision"""
        return (context.current_skill_id is not None and 
                context.current_target_id is not None and
                context.current_skill_tier is not None)
    
    def process(self, context: BattleContext) -> None:
        """Validate resource requirements for the chosen action"""
        context.log("Validating resource requirements")
        
        actor = context.get_current_actor()
        skills_db = context.get_skills_db()
        
        if not actor or not skills_db:
            context.set_error("Missing actor or skills database")
            return
        
        try:
            # Get skill parameters
            params: _SkillTierParams = skills_db.get_tier_params(
                context.current_skill_id, context.current_skill_tier
            )
            
            # Check qi requirements
            if actor.qi < params.qi_cost:
                context.log(f"Insufficient qi: need {params.qi_cost}, have {actor.qi}")
                context.set_error(f"Actor {actor.id} lacks qi for {context.current_skill_id}")
                context.skip_remaining_processors()
                return
            
            # Check cooldown status
            current_cooldown = actor.cooldowns.get(context.current_skill_id, 0)
            if current_cooldown > 0:
                context.log(f"Skill on cooldown: {current_cooldown} turns remaining")
                context.set_error(f"Skill {context.current_skill_id} on cooldown for {actor.id}")
                context.skip_remaining_processors()
                return
            
            context.log(f"Resource validation passed: qi_cost={params.qi_cost}, cooldown={params.cooldown}")
            
        except Exception as e:
            context.set_error(f"Failed to validate resources: {str(e)}")
            context.skip_remaining_processors()