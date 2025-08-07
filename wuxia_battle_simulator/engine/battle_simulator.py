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
                 cooldown: int, hit_chance: float, critical_chance: float, tier_name: str = "") -> None:
        self.base_damage = base_damage
        self.power_multiplier = power_multiplier
        self.qi_cost = qi_cost
        self.cooldown = cooldown
        self.hit_chance = hit_chance
        self.critical_chance = critical_chance
        self.tier_name = tier_name


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

    def step(self) -> Optional[BattleEvent]:
        """
        Advances ATB until an actor can act, then resolves the action into a BattleEvent.
        Returns None if no action occurred this tick.
        """
        if self.state.is_battle_over():
            return None

        views = self._actor_views()
        chosen_id = self.clock.tick(views)
        # Sync back time_units after tick
        self._sync_time_units_back(views)

        if not chosen_id:
            return None

        actor = self.state.get_actor(chosen_id)
        if not actor.is_alive():
            return None

        # Decrement actor cooldowns at start of their turn (per-actor action semantics)
        self.state.decrement_cooldowns(actor.id)

        # Ask AI for action
        try:
            skill_id, target_id, tier = self.ai.choose_action(self.state, actor)
        except Exception:
            # If AI cannot choose, skip the action (could produce a 'defend' no-op)
            return None

        target = self.state.get_actor(target_id) if target_id else None

        # If no skill chosen (fallback), emit defend/dodge no-op
        if not skill_id or tier <= 0 or not target:
            return BattleEvent(
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
            )

        # Resolve skill tiers and parameters via AI's skills_db
        skills_db = getattr(self.ai, "_skills", None)
        if skills_db is None:
            raise RuntimeError("Skills DB not available on AI")
        params: _SkillTierParams = skills_db.get_tier_params(skill_id, tier)

        final_damage, outcome, bucket = self.compute_damage(actor, target, params, self.rng)

        # Apply resource and cooldown updates
        self.state.consume_qi(actor.id, params.qi_cost)
        if params.cooldown > 0:
            self.state.set_cooldown(actor.id, skill_id, params.cooldown)

        pre_hp = target.hp
        self.state.apply_damage(target.id, final_damage)
        post_hp = self.state.get_actor(target.id).hp
        remaining_hp_percent = post_hp / target.stats.max_hp if target.stats.max_hp > 0 else 0.0
        cd_remaining = self.state.get_actor(actor.id).cooldowns.get(skill_id, 0)

        # Determine event type
        event_type: EventType = "attack"
        if outcome == "critical":
            event_type = "critical"
        elif outcome == "miss":
            event_type = "dodge"
        # 'defend' would be emitted by no-op branch above

        ev = BattleEvent(
            timestamp=self.clock.current_time(),
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
        return ev

    def run_to_completion(self, max_steps: int = 1000) -> List[BattleEvent]:
        events: List[BattleEvent] = []
        steps = 0
        while not self.state.is_battle_over() and steps < max_steps:
            ev = self.step()
            if ev:
                events.append(ev)
            steps += 1
        return events

    def compute_damage(self, actor, target, params: _SkillTierParams, rng) -> Tuple[int, OutcomeType, DamageBucket]:
        # Base damage formula
        base_damage = (actor.stats.strength * params.power_multiplier) + params.base_damage
        defense_reduction = target.stats.defense * 0.5
        final_damage = max(1.0, base_damage - defense_reduction)

        # Critical check
        if rng.random() < (params.critical_chance + actor.stats.agility * 0.01):
            final_damage *= 1.5
            outcome: OutcomeType = "critical"
        else:
            outcome = "hit"

        # Hit/Miss check overrides outcome if miss
        if rng.random() > (params.hit_chance + actor.stats.agility * 0.02 - target.stats.agility * 0.01):
            outcome = "miss"
            final_damage = 0.0

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

    def map_event_for_narration(self, ev: BattleEvent) -> Dict[str, Any]:
        """
        Provide a context dict for narrator with Chinese narrative_type mapping handled externally.
        Includes commonly referenced fields for templates: attacker, target, skill, tier_name, etc.
        """
        # Try to obtain skill/tier names where available
        skills_db = getattr(self.ai, "_skills", None)

        skill_name = ""
        tier_name = ""
        visual_effects = []
        sound_effects = []
        skill_type = "攻击"
        if skills_db and ev.skill_id and ev.skill_tier:
            try:
                skill_name = skills_db.get_skill_name(ev.skill_id)
                tier_name = skills_db.get_tier_name(ev.skill_id, ev.skill_tier)
                skill_type = skills_db.get_skill_type(ev.skill_id)
                # Optional: expose effects arrays if present in DB
                p = skills_db.get_tier_params(ev.skill_id, ev.skill_tier)
                visual_effects = getattr(p, "visual_effects", []) if hasattr(p, "visual_effects") else []
                sound_effects = getattr(p, "sound_effects", []) if hasattr(p, "sound_effects") else []
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
            "target_faction": target.faction if target else ""
        }
        return context