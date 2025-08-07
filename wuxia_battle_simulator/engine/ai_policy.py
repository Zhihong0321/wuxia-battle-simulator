from typing import Tuple, List, Optional
from dataclasses import dataclass

# Heuristic AI: choose highest expected damage per action within qi/cooldown; target lowest HP.


@dataclass
class _SkillTierParams:
    base_damage: int
    power_multiplier: float
    qi_cost: int
    cooldown: int
    hit_chance: float
    critical_chance: float


class SkillDB:
    """
    Minimal interface expectation for skills DB used by AI and simulator.
    The real implementation will live under utils.data_loader.DataManager.
    """
    def get_tier_params(self, skill_id: str, tier: int) -> _SkillTierParams:
        raise NotImplementedError()

    def get_tier_name(self, skill_id: str, tier: int) -> str:
        raise NotImplementedError()


class HeuristicAI:
    def __init__(self, rng, skills_db: SkillDB):
        self._rng = rng
        self._skills = skills_db

    def _expected_damage(self, actor, target, params: _SkillTierParams) -> float:
        # P_hit and P_crit approximations with agility influence, clamped 0..1
        a_agl = getattr(actor.stats, "agility", 0)
        t_agl = getattr(target.stats, "agility", 0)

        p_hit = max(0.0, min(1.0, params.hit_chance + a_agl * 0.02 - t_agl * 0.01))
        p_crit = max(0.0, min(1.0, params.critical_chance + a_agl * 0.01))

        base = (actor.stats.strength * params.power_multiplier) + params.base_damage - (target.stats.defense * 0.5)
        base = max(1.0, base)
        # Crit adds +50% extra on top of base
        exp = p_hit * (base + p_crit * (0.5 * base))
        return exp

    def _viable_skills(self, actor) -> List[Tuple[str, int]]:
        viable: List[Tuple[str, int]] = []
        for eq in actor.skills:
            # cooldown 0 and qi sufficient
            cd_rem = actor.cooldowns.get(eq.skill_id, 0)
            params = self._safe_params(eq.skill_id, eq.tier)
            if params and cd_rem == 0 and params.qi_cost <= actor.qi:
                viable.append((eq.skill_id, eq.tier))
        return viable

    def _safe_params(self, skill_id: str, tier: int) -> Optional[_SkillTierParams]:
        try:
            return self._skills.get_tier_params(skill_id, tier)
        except Exception:
            return None

    def choose_action(self, state, actor) -> Tuple[str, str, int]:
        """
        Returns (skill_id, target_id, tier). Raises if no opponents.
        Strategy:
          - target lowest HP opponent (tie: lower defense)
          - among viable skills, maximize expected damage / (cooldown+1)
          - tie-break: higher tier; then skill_id lexicographically
        """
        opponents = state.get_opponents(actor.id)
        if not opponents:
            raise RuntimeError("No opponents available")

        # Pick target
        target = sorted(opponents, key=lambda c: (c.hp, c.stats.defense))[0]

        # Choose skill
        candidates = self._viable_skills(actor)
        if not candidates:
            # Fallback: pick any skill with zero qi_cost if exists (defend/dodge-like),
            # otherwise do nothing (could be modeled as 'defend' action in simulator)
            for eq in actor.skills:
                params = self._safe_params(eq.skill_id, eq.tier)
                if params and params.qi_cost == 0:
                    return (eq.skill_id, target.id, eq.tier)
            return ("", target.id, 0)

        def score(item: Tuple[str, int]) -> Tuple[float, int, str]:
            sid, tier = item
            params = self._safe_params(sid, tier)
            if not params:
                return (-1.0, tier, sid)
            exp = self._expected_damage(actor, target, params)
            dps_proxy = exp / (params.cooldown + 1.0)
            # Higher is better; tie-breakers invert sort later
            return (dps_proxy, tier, sid)

        best = sorted(candidates, key=score, reverse=True)[0]
        return (best[0], target.id, best[1])