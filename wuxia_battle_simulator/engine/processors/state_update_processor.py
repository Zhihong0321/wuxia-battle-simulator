from ..step_processor import StepProcessor
from ..battle_context import BattleContext


class StateUpdateProcessor(StepProcessor):
    """
    Handles state updates including applying damage, updating resources (Qi),
    and managing cooldowns for characters.
    """
    
    def __init__(self):
        super().__init__("State Update Processor", critical=True)
    
    def can_process(self, context: BattleContext) -> bool:
        """Always process state updates"""
        return True
    
    def process(self, context: BattleContext) -> None:
        """Apply state changes to characters"""
        context.log("Updating character states")
        
        try:
            # Apply damage to target
            self._apply_damage(context)
            
            # Update actor resources and cooldowns
            self._update_actor_resources(context)
            
            # Update actor skill cooldowns
            self._update_actor_cooldowns(context)
            
            context.log("State updates completed")
            
        except Exception as e:
            context.set_error(f"Failed to update states: {str(e)}")
    
    def _apply_damage(self, context: BattleContext) -> None:
        """Apply calculated damage to the target"""
        if not context.current_target_id or context.damage_amount <= 0:
            return
        
        target = context.get_current_target()
        if not target:
            context.log("No target found for damage application")
            return
        
        # Apply damage
        old_hp = target.hp
        target.hp = max(0, target.hp - context.damage_amount)
        
        context.log(f"Applied {context.damage_amount} damage to {target.id} (HP: {old_hp} -> {target.hp})")
        
        # Check if target is defeated
        if target.hp <= 0:
            context.log(f"Target {target.id} has been defeated")
    
    def _update_actor_resources(self, context: BattleContext) -> None:
        """Update actor's Qi based on skill usage"""
        if not context.current_skill_id or not context.current_skill_tier:
            return
        
        actor = context.get_current_actor()
        skills_db = context.get_skills_db()
        
        if not actor or not skills_db:
            return
        
        try:
            # Get skill parameters to determine Qi cost
            skill_params = skills_db.get_tier_params(context.current_skill_id, context.current_skill_tier)
            qi_cost = skill_params.qi_cost
            
            # Deduct Qi
            old_qi = actor.qi
            actor.qi = max(0, actor.qi - qi_cost)
            
            context.log(f"Actor {actor.id} used {qi_cost} Qi (Qi: {old_qi} -> {actor.qi})")
            
        except Exception as e:
            context.log(f"Failed to update actor resources: {str(e)}")
    
    def _update_actor_cooldowns(self, context: BattleContext) -> None:
        """Update actor's skill cooldowns"""
        if not context.current_skill_id or not context.current_skill_tier:
            return
        
        actor = context.get_current_actor()
        skills_db = context.get_skills_db()
        
        if not actor or not skills_db:
            return
        
        try:
            # Get skill parameters to determine cooldown
            skill_params = skills_db.get_tier_params(context.current_skill_id, context.current_skill_tier)
            cooldown_duration = skill_params.cooldown
            
            # Find the skill in actor's equipped skills and set cooldown
            for equipped_skill in actor.skills:
                if equipped_skill.skill_id == context.current_skill_id:
                    old_cooldown = equipped_skill.cooldown_remaining
                    equipped_skill.cooldown_remaining = cooldown_duration
                    context.log(f"Set cooldown for {context.current_skill_id}: {old_cooldown} -> {cooldown_duration}")
                    break
            
        except Exception as e:
            context.log(f"Failed to update actor cooldowns: {str(e)}")