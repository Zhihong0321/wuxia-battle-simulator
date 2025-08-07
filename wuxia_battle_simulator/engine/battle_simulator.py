from typing import List, Optional, Dict, Any, Tuple, Literal
from dataclasses import dataclass
import math


EventType = Literal["attack", "defend", "dodge", "critical"]
OutcomeType = Literal["hit", "miss", "blocked", "critical"]
DamageBucket = Literal["low", "medium", "high"]


@dataclass
class BattleEvent:
    timestamp: float
    event_type: EventType
    actor: str
    target: Optional[str]
    skill_id: Optional[str]
    skill_tier: Optional[int]
    outcome: OutcomeType
    damage: int
    damage_percent: DamageBucket
    remaining_hp_percent: float
    qi_cost: int
    cooldown_remaining: int


class _SkillTierParams:
    def __init__(self, base_damage: int, power_multiplier: float, qi_cost: int,
                 cooldown: int, hit_chance: float, critical_chance: float, tier_name: str = "",
                 miss_chance: float = 0.0, partial_miss_chance: float = 0.0,
                 partial_miss_min_reduction: float = 0.0, partial_miss_max_reduction: float = 0.0,
                 damage_reduction: float = 0.0) -> None:
        self.base_damage = base_damage
        self.power_multiplier = power_multiplier
        self.qi_cost = qi_cost
        self.cooldown = cooldown
        self.hit_chance = hit_chance
        self.critical_chance = critical_chance
        self.tier_name = tier_name
        self.miss_chance = miss_chance
        self.partial_miss_chance = partial_miss_chance
        self.partial_miss_min_reduction = partial_miss_min_reduction
        self.partial_miss_max_reduction = partial_miss_max_reduction
        self.damage_reduction = damage_reduction


class SkillDBIface:
    def get_tier_params(self, skill_id: str, tier: int) -> _SkillTierParams:
        raise NotImplementedError()

    def get_tier_name(self, skill_id: str, tier: int) -> str:
        raise NotImplementedError()

    def get_skill_name(self, skill_id: str) -> str:
        raise NotImplementedError()

    def get_skill_type(self, skill_id: str) -> str:
        raise NotImplementedError()


class BattleSimulator:
    """
    Orchestrates the ATB loop, AI decisions, and action resolution.
    Expects injected AI, ATB clock, RNG, and game state.
    """
    def __init__(self, state, ai, clock, rng) -> None:
        self.state = state
        self.ai = ai
        self.clock = clock
        self.rng = rng

    def _actor_views(self):
        # Adapter for ATBClock expected structure
        from .game_state import CharacterState  # type: ignore
        views = []
        for c in self.state.living():
            views.append(type("ActorView", (), {
                "actor_id": c.id,
                "agility": c.stats.agility,
                "time_units": c.time_units
            })())
        return views

    def _sync_time_units_back(self, views) -> None:
        for v in views:
            self.state.get_actor(v.actor_id).time_units = v.time_units

    def step(self) -> List[BattleEvent]:
        """
        Advances ATB until an actor can act, then resolves the action into a list of BattleEvents.
        Returns empty list if no action occurred this tick.
        """
        if self.state.is_battle_over():
            return []

        views = self._actor_views()
        chosen_id = self.clock.tick(views)
        # Sync back time_units after tick
        self._sync_time_units_back(views)

        if not chosen_id:
            return []

        actor = self.state.get_actor(chosen_id)
        if not actor.is_alive():
            return []

        # Decrement actor cooldowns at start of their turn (per-actor action semantics)
        self.state.decrement_cooldowns(actor.id)

        # Ask AI for action
        try:
            skill_id, target_id, tier = self.ai.choose_action(self.state, actor)
        except Exception:
            # If AI cannot choose, skip the action (could produce a 'defend' no-op)
            return []

        target = self.state.get_actor(target_id) if target_id else None

        # If no skill chosen (fallback), emit defend/dodge no-op
        if not skill_id or tier <= 0 or not target:
            return [BattleEvent(
                timestamp=self.clock.current_time(),
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
            )]

        # Resolve skill tiers and parameters via AI's skills_db
        skills_db = getattr(self.ai, "_skills", None)
        if skills_db is None:
            raise RuntimeError("Skills DB not available on AI")
        params: _SkillTierParams = skills_db.get_tier_params(skill_id, tier)

        # Generate events for the complete battle sequence
        events = []
        timestamp = self.clock.current_time()
        
        # Get movement and defense skill parameters
        movement_skill_params = self._get_target_movement_skill_params(target)
        defense_skill_params = self._get_target_defense_skill_params(target)
        
        # Calculate hit result and damage
        final_damage, outcome, bucket, hit_result = self.compute_damage_with_details(actor, target, params, self.rng)
        
        # Event 1: Movement skill (dodge attempt) if target has movement skill
        if movement_skill_params.miss_chance > 0 or movement_skill_params.partial_miss_chance > 0:
            movement_skill_id = self._get_target_movement_skill_id(target)
            movement_tier = self._get_target_movement_skill_tier(target)
            
            dodge_outcome = "miss" if hit_result == "miss" else ("hit" if hit_result == "partial_hit" else "blocked")
            dodge_event = BattleEvent(
                timestamp=timestamp,
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
            events.append(dodge_event)
        
        # Event 2: Defense skill if target has defense skill and attack hits
        if defense_skill_params.damage_reduction > 0 and hit_result != "miss":
            defense_skill_id = self._get_target_defense_skill_id(target)
            defense_tier = self._get_target_defense_skill_tier(target)
            
            defense_event = BattleEvent(
                timestamp=timestamp,
                event_type="defend",
                actor=target.id,
                target=actor.id,
                skill_id=defense_skill_id,
                skill_tier=defense_tier,
                outcome="blocked",
                damage=0,
                damage_percent="low",
                remaining_hp_percent=target.hp / target.stats.max_hp,
                qi_cost=0,
                cooldown_remaining=0
            )
            events.append(defense_event)
        
        # Apply resource and cooldown updates
        self.state.consume_qi(actor.id, params.qi_cost)
        if params.cooldown > 0:
            self.state.set_cooldown(actor.id, skill_id, params.cooldown)

        # Apply damage
        pre_hp = target.hp
        self.state.apply_damage(target.id, final_damage)
        post_hp = self.state.get_actor(target.id).hp
        remaining_hp_percent = post_hp / target.stats.max_hp if target.stats.max_hp > 0 else 0.0
        cd_remaining = self.state.get_actor(actor.id).cooldowns.get(skill_id, 0)

        # Event 3: Attack result
        event_type: EventType = "attack"
        if outcome == "critical":
            event_type = "critical"
        elif outcome == "miss":
            event_type = "dodge"

        attack_event = BattleEvent(
            timestamp=timestamp,
            event_type=event_type,
            actor=actor.id,
            target=target.id,
            skill_id=skill_id,
            skill_tier=tier,
            outcome=outcome,
            damage=final_damage,
            damage_percent=bucket,
            remaining_hp_percent=remaining_hp_percent,
            qi_cost=params.qi_cost,
            cooldown_remaining=cd_remaining
        )
        events.append(attack_event)
        
        return events

    def run_to_completion(self, max_steps: int = 1000) -> List[BattleEvent]:
        events: List[BattleEvent] = []
        steps = 0
        while not self.state.is_battle_over() and steps < max_steps:
            step_events = self.step()
            if step_events:
                events.extend(step_events)
            steps += 1
        return events

    def compute_damage(self, actor, target, params: _SkillTierParams, rng) -> Tuple[int, OutcomeType, DamageBucket]:
        # Base damage formula
        base_damage = (actor.stats.strength * params.power_multiplier) + params.base_damage
        defense_reduction = target.stats.defense * 0.5
        final_damage = max(1.0, base_damage - defense_reduction)
        
        # Step 1: Check against target's movement skill for hit/miss/partial hit
        movement_skill_params = self._get_target_movement_skill_params(target)
        hit_result = self._calculate_hit_result(actor, target, params, movement_skill_params, rng)
        
        if hit_result == "miss":
            return 0, "miss", "low"
        elif hit_result == "partial_hit":
            # Apply partial miss damage reduction
            reduction_range = movement_skill_params.partial_miss_max_reduction - movement_skill_params.partial_miss_min_reduction
            reduction = movement_skill_params.partial_miss_min_reduction + (rng.random() * reduction_range)
            final_damage *= (1.0 - reduction)
        
        # Step 2: Critical hit calculation (only if hit or partial hit)
        outcome: OutcomeType = "hit"
        if rng.random() < (params.critical_chance + actor.stats.agility * 0.01):
            final_damage *= 1.5
            outcome = "critical"
        
        # Step 3: Apply defense skill damage reduction
        defense_skill_params = self._get_target_defense_skill_params(target)
        if defense_skill_params and defense_skill_params.damage_reduction > 0:
            final_damage *= (1.0 - defense_skill_params.damage_reduction)
        
        final_damage_int = int(math.floor(final_damage))

        # Damage percent bucket
        # Map strictly by percent of target max HP:
        #  - low:   < 10%
        #  - medium: >= 10% and <= 25%
        #  - high:  > 25%
        ratio = 0.0 if target.stats.max_hp <= 0 else (final_damage_int / float(target.stats.max_hp))
        if ratio < 0.10:
            bucket: DamageBucket = "low"
        elif ratio <= 0.25:
            bucket = "medium"
        else:
            bucket = "high"

        return final_damage_int, outcome, bucket
    
    def compute_damage_with_details(self, actor, target, params: _SkillTierParams, rng) -> Tuple[int, OutcomeType, DamageBucket, str]:
        """Enhanced damage computation that returns hit result details"""
        # Base damage formula
        base_damage = (actor.stats.strength * params.power_multiplier) + params.base_damage
        defense_reduction = target.stats.defense * 0.5
        final_damage = max(1.0, base_damage - defense_reduction)
        
        # Step 1: Check against target's movement skill for hit/miss/partial hit
        movement_skill_params = self._get_target_movement_skill_params(target)
        hit_result = self._calculate_hit_result(actor, target, params, movement_skill_params, rng)
        
        if hit_result == "miss":
            return 0, "miss", "low", hit_result
        elif hit_result == "partial_hit":
            # Apply partial miss damage reduction
            reduction_range = movement_skill_params.partial_miss_max_reduction - movement_skill_params.partial_miss_min_reduction
            reduction = movement_skill_params.partial_miss_min_reduction + (rng.random() * reduction_range)
            final_damage *= (1.0 - reduction)
        
        # Step 2: Critical hit calculation (only if hit or partial hit)
        outcome: OutcomeType = "hit"
        if rng.random() < (params.critical_chance + actor.stats.agility * 0.01):
            final_damage *= 1.5
            outcome = "critical"
        
        # Step 3: Apply defense skill damage reduction
        defense_skill_params = self._get_target_defense_skill_params(target)
        if defense_skill_params and defense_skill_params.damage_reduction > 0:
            final_damage *= (1.0 - defense_skill_params.damage_reduction)
        
        final_damage_int = int(math.floor(final_damage))

        # Damage percent bucket
        ratio = 0.0 if target.stats.max_hp <= 0 else (final_damage_int / float(target.stats.max_hp))
        if ratio < 0.10:
            bucket: DamageBucket = "low"
        elif ratio <= 0.25:
            bucket = "medium"
        else:
            bucket = "high"

        return final_damage_int, outcome, bucket, hit_result
    
    def _get_target_movement_skill_params(self, target) -> _SkillTierParams:
        """Get movement skill parameters for the target character"""
        # Find equipped movement skill
        for equipped_skill in target.skills:
            skills_db = getattr(self.ai, "_skills", None)
            if skills_db is None:
                continue
            skill_type = skills_db.get_skill_type(equipped_skill.skill_id)
            if skill_type in ["闪避", "movement"]:
                return skills_db.get_tier_params(equipped_skill.skill_id, equipped_skill.tier)
        
        # Return default params if no movement skill equipped
        return _SkillTierParams(
            base_damage=0, power_multiplier=0.0, qi_cost=0, cooldown=0,
            hit_chance=0.0, critical_chance=0.0, tier_name="",
            miss_chance=0.0, partial_miss_chance=0.0,
            partial_miss_min_reduction=0.0, partial_miss_max_reduction=0.0,
            damage_reduction=0.0
        )
    
    def _get_target_movement_skill_id(self, target) -> Optional[str]:
        """Get movement skill ID for the target character"""
        for equipped_skill in target.skills:
            skills_db = getattr(self.ai, "_skills", None)
            if skills_db is None:
                continue
            skill_type = skills_db.get_skill_type(equipped_skill.skill_id)
            if skill_type in ["闪避", "movement"]:
                return equipped_skill.skill_id
        return None
    
    def _get_target_movement_skill_tier(self, target) -> int:
        """Get movement skill tier for the target character"""
        for equipped_skill in target.skills:
            skills_db = getattr(self.ai, "_skills", None)
            if skills_db is None:
                continue
            skill_type = skills_db.get_skill_type(equipped_skill.skill_id)
            if skill_type in ["闪避", "movement"]:
                return equipped_skill.tier
        return 1
    
    def _get_target_defense_skill_id(self, target) -> Optional[str]:
        """Get defense skill ID for the target character"""
        for equipped_skill in target.skills:
            skills_db = getattr(self.ai, "_skills", None)
            if skills_db is None:
                continue
            skill_type = skills_db.get_skill_type(equipped_skill.skill_id)
            if skill_type in ["抵挡", "defense"]:
                return equipped_skill.skill_id
        return None
    
    def _get_target_defense_skill_tier(self, target) -> int:
        """Get defense skill tier for the target character"""
        for equipped_skill in target.skills:
            skills_db = getattr(self.ai, "_skills", None)
            if skills_db is None:
                continue
            skill_type = skills_db.get_skill_type(equipped_skill.skill_id)
            if skill_type in ["抵挡", "defense"]:
                return equipped_skill.tier
        return 1
    
    def _get_target_defense_skill_params(self, target) -> Optional[_SkillTierParams]:
        """Get defense skill parameters for the target character"""
        # Find equipped defense skill
        for equipped_skill in target.skills:
            skills_db = getattr(self.ai, "_skills", None)
            if skills_db is None:
                continue
            skill_type = skills_db.get_skill_type(equipped_skill.skill_id)
            if skill_type in ["抵挡", "defense"]:
                return skills_db.get_tier_params(equipped_skill.skill_id, equipped_skill.tier)
        
        return None
    
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

    def map_event_for_narration(self, ev: BattleEvent) -> Dict[str, Any]:
        """
        Provide a context dict for narrator with Chinese narrative_type mapping handled externally.
        Includes commonly referenced fields for templates: attacker, target, skill, tier_name, etc.
        Additionally exposes per-skill, per-tier narrative_template if defined in SkillDB.
        """
        # Try to obtain skill/tier names where available
        skills_db = getattr(self.ai, "_skills", None)

        skill_name = ""
        tier_name = ""
        visual_effects = []
        sound_effects = []
        narrative_template = ""
        skill_type = "攻击"
        if skills_db and ev.skill_id and ev.skill_tier:
            try:
                skill_name = skills_db.get_skill_name(ev.skill_id)
                tier_name = skills_db.get_tier_name(ev.skill_id, ev.skill_tier)
                skill_type = skills_db.get_skill_type(ev.skill_id)
                # Optional: expose effects arrays and tier narrative if present in DB
                p = skills_db.get_tier_params(ev.skill_id, ev.skill_tier)
                visual_effects = getattr(p, "visual_effects", []) if hasattr(p, "visual_effects") else []
                sound_effects = getattr(p, "sound_effects", []) if hasattr(p, "sound_effects") else []
                narrative_template = getattr(p, "narrative_template", "") if hasattr(p, "narrative_template") else ""
            except Exception:
                pass

        actor = self.state.get_actor(ev.actor)
        target = self.state.get_actor(ev.target) if ev.target else None

        # Map internal event_type to Chinese label for templates
        type_map = {"attack": "攻击", "defend": "抵挡", "dodge": "闪避", "critical": "暴击"}
        narrative_type = type_map.get(ev.event_type, "攻击")

        context: Dict[str, Any] = {
            "timestamp": ev.timestamp,
            "narrative_type": narrative_type,
            "attacker": actor.name,
            "target": target.name if target else "",
            "skill": skill_name,
            "tier_name": tier_name,
            "damage": ev.damage,
            "faction": actor.faction,
            "hp_percent": round(ev.remaining_hp_percent * 100.0, 1),
            "faction_terminology": actor.faction_terminology,
            "visual_effects": visual_effects,
            "sound_effects": sound_effects,
            "hit": ev.outcome != "miss",
            "critical": ev.outcome == "critical",
            "damage_percent": ev.damage_percent,
            "actor_faction": actor.faction,
            "target_faction": target.faction if target else "",
            # New: per-tier narrative text
            "tier_narrative_template": narrative_template,
        }
        return context