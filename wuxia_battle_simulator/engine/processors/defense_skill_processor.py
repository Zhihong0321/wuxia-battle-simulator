from ..step_processor import StepProcessor
from ..battle_context import BattleContext
from ..battle_simulator import BattleEvent, _SkillTierParams


class DefenseSkillProcessor(StepProcessor):
    """
    Handles target's defense skills (damage reduction abilities).
    Processes defensive mechanics and generates defense events.
    """
    
    def __init__(self):
        super().__init__("Defense Skill Processor", critical=False)
    
    def can_process(self, context: BattleContext) -> bool:
        """Process if target has defense skills and attack hits"""
        if not context.current_target_id or context.hit_result == "miss":
            return False
        
        target = context.get_current_target()
        if not target:
            return False
        
        # Check if target has defense skills
        defense_params = self._get_target_defense_skill_params(context, target)
        return defense_params is not None and defense_params.damage_reduction > 0
    
    def process(self, context: BattleContext) -> None:
        """Process defense skill activation"""
        context.log("Processing defense skill")
        
        target = context.get_current_target()
        if not target:
            context.set_error("No target for defense processing")
            return
        
        try:
            # Get defense skill info
            defense_skill_id = self._get_target_defense_skill_id(context, target)
            defense_tier = self._get_target_defense_skill_tier(context, target)
            
            if defense_skill_id:
                defense_event = BattleEvent(
                    timestamp=context.clock.current_time(),
                    event_type="defend",
                    actor=target.id,
                    target=target.id,
                    skill_id=defense_skill_id,
                    skill_tier=defense_tier,
                    outcome="blocked",
                    damage=0,
                    damage_percent="low",
                    remaining_hp_percent=target.hp / target.stats.max_hp,
                    qi_cost=0,
                    cooldown_remaining=0
                )
                
                context.add_event(defense_event)
                context.log(f"Defense skill activated: {defense_skill_id}")
            
        except Exception as e:
            context.set_error(f"Failed to process defense skill: {str(e)}")
    
    def _get_target_defense_skill_params(self, context: BattleContext, target) -> _SkillTierParams:
        """Get defense skill parameters for the target character"""
        skills_db = context.get_skills_db()
        if not skills_db:
            return None
        
        # Find equipped defense skill
        for equipped_skill in target.skills:
            try:
                skill_type = skills_db.get_skill_type(equipped_skill.skill_id)
                if skill_type in ["抵挡", "defense"]:
                    return skills_db.get_tier_params(equipped_skill.skill_id, equipped_skill.tier)
            except Exception:
                continue
        
        return None
    
    def _get_target_defense_skill_id(self, context: BattleContext, target) -> str:
        """Get defense skill ID for the target character"""
        skills_db = context.get_skills_db()
        if not skills_db:
            return None
        
        for equipped_skill in target.skills:
            try:
                skill_type = skills_db.get_skill_type(equipped_skill.skill_id)
                if skill_type in ["抵挡", "defense"]:
                    return equipped_skill.skill_id
            except Exception:
                continue
        return None
    
    def _get_target_defense_skill_tier(self, context: BattleContext, target) -> int:
        """Get defense skill tier for the target character"""
        skills_db = context.get_skills_db()
        if not skills_db:
            return 1
        
        for equipped_skill in target.skills:
            try:
                skill_type = skills_db.get_skill_type(equipped_skill.skill_id)
                if skill_type in ["抵挡", "defense"]:
                    return equipped_skill.tier
            except Exception:
                continue
        return 1