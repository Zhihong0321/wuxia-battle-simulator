import math
from ..step_processor import StepProcessor
from ..battle_context import BattleContext
from ..battle_simulator import _SkillTierParams


class DamageCalculationProcessor(StepProcessor):
    """
    Handles damage calculation including base damage, critical hits, and damage reduction.
    Computes final damage amount and outcome type.
    """
    
    def __init__(self):
        super().__init__("Damage Calculation Processor", critical=True)
    
    def can_process(self, context: BattleContext) -> bool:
        """Process if we have a valid attack scenario"""
        return (context.current_skill_id is not None and 
                context.current_target_id is not None and
                context.current_skill_tier is not None)
    
    def process(self, context: BattleContext) -> None:
        """Calculate damage and outcome"""
        context.log("Calculating damage")
        
        actor = context.get_current_actor()
        target = context.get_current_target()
        skills_db = context.get_skills_db()
        
        if not actor or not target or not skills_db:
            context.set_error("Missing required components for damage calculation")
            return
        
        try:
            # Get attack skill parameters
            attack_params: _SkillTierParams = skills_db.get_tier_params(
                context.current_skill_id, context.current_skill_tier
            )
            
            # Calculate damage based on hit result
            if context.hit_result == "miss":
                context.damage_amount = 0
                context.outcome = "miss"
                context.damage_bucket = "low"
                context.log("Attack missed - no damage")
                return
            
            # Calculate base damage
            base_damage = (actor.stats.strength * attack_params.power_multiplier) + attack_params.base_damage
            defense_reduction = target.stats.defense * 0.5
            final_damage = max(1.0, base_damage - defense_reduction)
            
            # Apply partial hit reduction if applicable
            if context.hit_result == "partial_hit":
                movement_params = self._get_target_movement_skill_params(context, target)
                if movement_params:
                    reduction_range = movement_params.partial_miss_max_reduction - movement_params.partial_miss_min_reduction
                    reduction = movement_params.partial_miss_min_reduction + (context.rng.random() * reduction_range)
                    final_damage *= (1.0 - reduction)
                    context.log(f"Partial hit damage reduction: {reduction:.2%}")
            
            # Check for critical hit
            context.outcome = "hit"
            crit_chance = attack_params.critical_chance + (actor.stats.agility * 0.01)
            if context.rng.random() < crit_chance:
                final_damage *= 1.5
                context.outcome = "critical"
                context.log("Critical hit!")
            
            # Apply defense skill damage reduction
            defense_params = self._get_target_defense_skill_params(context, target)
            if defense_params and defense_params.damage_reduction > 0:
                final_damage *= (1.0 - defense_params.damage_reduction)
                context.log(f"Defense skill damage reduction: {defense_params.damage_reduction:.2%}")
            
            # Finalize damage
            context.damage_amount = int(math.floor(final_damage))
            
            # Calculate damage bucket
            context.damage_bucket = self._calculate_damage_bucket(context.damage_amount, target)
            
            context.log(f"Final damage: {context.damage_amount} ({context.damage_bucket})")
            
        except Exception as e:
            context.set_error(f"Failed to calculate damage: {str(e)}")
    
    def _get_target_movement_skill_params(self, context: BattleContext, target) -> _SkillTierParams:
        """Get movement skill parameters for partial hit calculations"""
        skills_db = context.get_skills_db()
        if not skills_db:
            return None
        
        for equipped_skill in target.skills:
            try:
                skill_type = skills_db.get_skill_type(equipped_skill.skill_id)
                if skill_type in ["闪避", "movement"]:
                    return skills_db.get_tier_params(equipped_skill.skill_id, equipped_skill.tier)
            except Exception:
                continue
        return None
    
    def _get_target_defense_skill_params(self, context: BattleContext, target) -> _SkillTierParams:
        """Get defense skill parameters for damage reduction"""
        skills_db = context.get_skills_db()
        if not skills_db:
            return None
        
        for equipped_skill in target.skills:
            try:
                skill_type = skills_db.get_skill_type(equipped_skill.skill_id)
                if skill_type in ["抵挡", "defense"]:
                    return skills_db.get_tier_params(equipped_skill.skill_id, equipped_skill.tier)
            except Exception:
                continue
        return None
    
    def _calculate_damage_bucket(self, damage: int, target) -> str:
        """Calculate damage bucket based on percentage of target's max HP"""
        if target.stats.max_hp <= 0:
            return "low"
        
        ratio = damage / float(target.stats.max_hp)
        
        if ratio < 0.10:
            return "low"
        elif ratio <= 0.25:
            return "medium"
        else:
            return "high"