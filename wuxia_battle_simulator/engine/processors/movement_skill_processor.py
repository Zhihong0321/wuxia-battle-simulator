from ..step_processor import StepProcessor
from ..battle_context import BattleContext
from ..battle_simulator import BattleEvent, _SkillTierParams


class MovementSkillProcessor(StepProcessor):
    """
    Handles target's movement skills (dodge attempts).
    Processes evasion mechanics and generates dodge events.
    """
    
    def __init__(self):
        super().__init__("Movement Skill Processor", critical=False)
    
    def can_process(self, context: BattleContext) -> bool:
        """Process if target has movement skills"""
        if not context.current_target_id:
            return False
        
        target = context.get_current_target()
        if not target:
            return False
        
        # Check if target has movement skills
        movement_params = self._get_target_movement_skill_params(context, target)
        return movement_params.miss_chance > 0 or movement_params.partial_miss_chance > 0
    
    def process(self, context: BattleContext) -> None:
        """Process movement skill dodge attempt"""
        context.log("Processing movement skill")
        
        actor = context.get_current_actor()
        target = context.get_current_target()
        skills_db = context.get_skills_db()
        
        if not actor or not target or not skills_db:
            context.set_error("Missing required components for movement processing")
            return
        
        try:
            # Get attack skill parameters
            attack_params: _SkillTierParams = skills_db.get_tier_params(
                context.current_skill_id, context.current_skill_tier
            )
            
            # Get movement skill parameters
            movement_params = self._get_target_movement_skill_params(context, target)
            
            # Calculate hit result
            hit_result = self._calculate_hit_result(actor, target, attack_params, movement_params, context.rng)
            context.hit_result = hit_result
            
            # Create dodge event if there was an evasion attempt
            movement_skill_id = self._get_target_movement_skill_id(context, target)
            movement_tier = self._get_target_movement_skill_tier(context, target)
            
            if movement_skill_id:
                dodge_outcome = "miss" if hit_result == "miss" else ("hit" if hit_result == "partial_hit" else "blocked")
                
                dodge_event = BattleEvent(
                    timestamp=context.clock.current_time(),
                    event_type="dodge",
                    actor=target.id,
                    target=actor.id,
                    skill_id=movement_skill_id,
                    skill_tier=movement_tier,
                    outcome=dodge_outcome,
                    damage=0,
                    damage_percent="low",
                    remaining_hp_percent=target.hp / target.stats.max_hp,
                    qi_cost=0,
                    cooldown_remaining=0
                )
                
                context.add_event(dodge_event)
                context.log(f"Movement skill result: {hit_result}")
            
        except Exception as e:
            context.set_error(f"Failed to process movement skill: {str(e)}")
    
    def _get_target_movement_skill_params(self, context: BattleContext, target) -> _SkillTierParams:
        """Get movement skill parameters for the target character"""
        skills_db = context.get_skills_db()
        if not skills_db:
            return self._default_movement_params()
        
        # Find equipped movement skill
        for equipped_skill in target.skills:
            try:
                skill_type = skills_db.get_skill_type(equipped_skill.skill_id)
                if skill_type in ["闪避", "movement"]:
                    return skills_db.get_tier_params(equipped_skill.skill_id, equipped_skill.tier)
            except Exception:
                continue
        
        return self._default_movement_params()
    
    def _get_target_movement_skill_id(self, context: BattleContext, target) -> str:
        """Get movement skill ID for the target character"""
        skills_db = context.get_skills_db()
        if not skills_db:
            return None
        
        for equipped_skill in target.skills:
            try:
                skill_type = skills_db.get_skill_type(equipped_skill.skill_id)
                if skill_type in ["闪避", "movement"]:
                    return equipped_skill.skill_id
            except Exception:
                continue
        return None
    
    def _get_target_movement_skill_tier(self, context: BattleContext, target) -> int:
        """Get movement skill tier for the target character"""
        skills_db = context.get_skills_db()
        if not skills_db:
            return 1
        
        for equipped_skill in target.skills:
            try:
                skill_type = skills_db.get_skill_type(equipped_skill.skill_id)
                if skill_type in ["闪避", "movement"]:
                    return equipped_skill.tier
            except Exception:
                continue
        return 1
    
    def _default_movement_params(self) -> _SkillTierParams:
        """Return default movement parameters when no movement skill is equipped"""
        return _SkillTierParams(
            base_damage=0, power_multiplier=0.0, qi_cost=0, cooldown=0,
            hit_chance=0.0, critical_chance=0.0, tier_name="",
            miss_chance=0.0, partial_miss_chance=0.0,
            partial_miss_min_reduction=0.0, partial_miss_max_reduction=0.0,
            damage_reduction=0.0
        )
    
    def _calculate_hit_result(self, actor, target, attack_params: _SkillTierParams, 
                             movement_params: _SkillTierParams, rng) -> str:
        """Calculate hit result: 'hit', 'miss', or 'partial_hit'"""
        # Calculate base hit chance with agility modifiers
        base_hit_chance = attack_params.hit_chance + (actor.stats.agility * 0.02) - (target.stats.agility * 0.01)
        base_hit_chance = max(0.0, min(1.0, base_hit_chance))
        
        # Check for complete miss first
        if rng.random() < movement_params.miss_chance:
            return "miss"
        
        # Check for partial miss
        if rng.random() < movement_params.partial_miss_chance:
            return "partial_hit"
        
        # Check base hit/miss
        if rng.random() > base_hit_chance:
            return "miss"
        
        return "hit"