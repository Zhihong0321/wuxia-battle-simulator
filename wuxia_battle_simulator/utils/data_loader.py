import json
from pathlib import Path
from typing import Dict, Any, List

from wuxia_battle_simulator.validation.validator import Validator, ValidationError
from wuxia_battle_simulator.utils.logger import get_logger
from wuxia_battle_simulator.engine.game_state import Stats, EquippedSkill, CharacterState, GameState
from wuxia_battle_simulator.engine.battle_simulator import _SkillTierParams as AITierParams  # reuse structure interface


class SkillTier:
    def __init__(self, tier: int, tier_name: str, parameters: Dict[str, Any],
                 visual_effects: List[str], sound_effects: List[str], narrative_template: str = "") -> None:
        self.tier = tier
        self.tier_name = tier_name
        self.parameters = parameters
        self.visual_effects = visual_effects
        self.sound_effects = sound_effects
        self.narrative_template = narrative_template


class SkillDef:
    def __init__(self, skill_id: str, name: str, type_: str, description: str, tiers: List[SkillTier]) -> None:
        self.id = skill_id
        self.name = name
        self.type = type_
        self.description = description
        self.tiers = {t.tier: t for t in tiers}


class SkillDB:
    """
    Runtime skills database used by AI and Simulator.
    Provides helpers to access tier parameters and names.
    """
    def __init__(self, skills: Dict[str, SkillDef]) -> None:
        self._skills = skills

    def get_tier_params(self, skill_id: str, tier: int) -> AITierParams:
        sd = self._skills[skill_id]
        st = sd.tiers[tier]
        p = st.parameters
        # Provide effects passthrough for narrator (optional)
        params = AITierParams(
            base_damage=int(p.get("base_damage", 0)),
            power_multiplier=float(p.get("power_multiplier", 0.0)),
            qi_cost=int(p.get("qi_cost", 0)),
            cooldown=int(p.get("cooldown", 0)),
            hit_chance=float(p.get("hit_chance", 1.0)),
            critical_chance=float(p.get("critical_chance", 0.0)),
            miss_chance=float(p.get("miss_chance", 0.0)),
            partial_miss_chance=float(p.get("partial_miss_chance", 0.0)),
            partial_miss_min_reduction=float(p.get("partial_miss_min_reduction", 0.0)),
            partial_miss_max_reduction=float(p.get("partial_miss_max_reduction", 0.0)),
            damage_reduction=float(p.get("damage_reduction", 0.0)),
        )
        # attach effects and narrative template for narrator mapping if available
        setattr(params, "visual_effects", st.visual_effects)
        setattr(params, "sound_effects", st.sound_effects)
        setattr(params, "narrative_template", getattr(st, "narrative_template", ""))
        setattr(params, "tier_name", st.tier_name)
        return params

    def get_tier_name(self, skill_id: str, tier: int) -> str:
        return self._skills[skill_id].tiers[tier].tier_name

    def get_skill_name(self, skill_id: str) -> str:
        return self._skills[skill_id].name

    def get_skill_type(self, skill_id: str) -> str:
        # Chinese label in data
        return self._skills[skill_id].type


class DataManager:
    def __init__(self, validator: Validator) -> None:
        self._validator = validator
        self._log = get_logger()

    def _read_json(self, path: Path) -> Any:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def load_config(self, path: Path) -> Dict[str, Any]:
        data = self._read_json(path)
        try:
            self._validator.validate(data, "config.schema.json")
        except ValidationError as e:
            self._log.warning(f"Config validation warning: {e}")
        return data

    def load_characters(self, path: Path) -> List[Dict[str, Any]]:
        data = self._read_json(path)
        # Could be array or dict keyed by id; normalize to array of dicts
        if isinstance(data, dict) and "characters" in data:
            items = data["characters"]
        else:
            items = data
        try:
            self._validator.validate({"characters": items}, "characters.schema.json")
        except ValidationError as e:
            self._log.warning(f"Characters validation warning: {e}")
        return items

    def load_skills(self, path: Path) -> SkillDB:
        data = self._read_json(path)
        if isinstance(data, dict) and "skills" in data:
            items = data["skills"]
        else:
            items = data
        try:
            self._validator.validate({"skills": items}, "skills.schema.json")
        except ValidationError as e:
            self._log.warning(f"Skills validation warning: {e}")

        skills: Dict[str, SkillDef] = {}
        for s in items:
            tiers: List[SkillTier] = []
            for t in s.get("tiers", []):
                tiers.append(
                    SkillTier(
                        tier=int(t.get("tier", 1)),
                        tier_name=str(t.get("tier_name", "")),
                        parameters=dict(t.get("parameters", {})),
                        visual_effects=list(t.get("visual_effects", [])),
                        sound_effects=list(t.get("sound_effects", [])),
                        narrative_template=str(t.get("narrative_template", "")),
                    )
                )
            sd = SkillDef(
                skill_id=s["id"],
                name=s.get("name", s["id"]),
                type_=s.get("type", "攻击"),
                description=s.get("description", ""),
                tiers=tiers
            )
            skills[sd.id] = sd
        return SkillDB(skills)

    def load_templates(self, path: Path) -> List[Dict[str, Any]]:
        data = self._read_json(path)
        items = data.get("templates", []) if isinstance(data, dict) else data
        try:
            self._validator.validate({"templates": items}, "templates.schema.json")
        except ValidationError as e:
            self._log.warning(f"Templates validation warning: {e}")
        return items

    def build_game_state(self, characters_def: List[Dict[str, Any]]) -> GameState:
        chars: List[CharacterState] = []
        for c in characters_def:
            stats = Stats(
                strength=int(c["stats"]["strength"]),
                agility=int(c["stats"]["agility"]),
                defense=int(c["stats"]["defense"]),
                max_hp=int(c["stats"]["max_hp"]),
                max_qi=int(c["stats"]["max_qi"]),
            )
            hp = int(c["stats"].get("hp", stats.max_hp))
            qi = int(c["stats"].get("qi", stats.max_qi))
            # Load equipped skills instead of all learned skills
            equipped_skills = []
            equipped_skills_data = c.get("equipped_skills", {})
            
            # Add equipped attack skill
            if "attack" in equipped_skills_data:
                attack_skill = equipped_skills_data["attack"]
                equipped_skills.append(EquippedSkill(
                    skill_id=attack_skill["skill_id"], 
                    tier=int(attack_skill.get("tier", 1))
                ))
            
            # Add equipped defense skill
            if "defense" in equipped_skills_data:
                defense_skill = equipped_skills_data["defense"]
                equipped_skills.append(EquippedSkill(
                    skill_id=defense_skill["skill_id"], 
                    tier=int(defense_skill.get("tier", 1))
                ))
            
            # Add equipped movement skill
            if "movement" in equipped_skills_data:
                movement_skill = equipped_skills_data["movement"]
                equipped_skills.append(EquippedSkill(
                    skill_id=movement_skill["skill_id"], 
                    tier=int(movement_skill.get("tier", 1))
                ))
            
            # Fallback: if no equipped skills, use learned skills for backward compatibility
            if not equipped_skills:
                equipped_skills = [EquippedSkill(skill_id=s["skill_id"], tier=int(s.get("tier", 1))) for s in c.get("skills", [])]
            
            cs = CharacterState(
                id=c["id"],
                name=c.get("name", c["id"]),
                faction=c.get("faction", ""),
                faction_terminology=c.get("faction_terminology", {}),
                stats=stats,
                hp=hp,
                qi=qi,
                cooldowns={},
                skills=equipped_skills,
                time_units=0.0
            )
            chars.append(cs)
        return GameState(chars)