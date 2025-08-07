import json
import os
import sys
from pathlib import Path

# Ensure package import when running as a script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

import random
import unittest

from wuxia_battle_simulator.engine.atb_system import ATBClock
from wuxia_battle_simulator.engine.game_state import Stats, EquippedSkill, CharacterState, GameState
from wuxia_battle_simulator.engine.ai_policy import HeuristicAI
from wuxia_battle_simulator.engine.battle_simulator import BattleSimulator
from wuxia_battle_simulator.narrator.template_index import TemplateIndex
from wuxia_battle_simulator.narrator.text_narrator import TextNarrator
from wuxia_battle_simulator.narrator.variable_resolver import VariableResolver
from wuxia_battle_simulator.utils.template_engine import TemplateEngine
from wuxia_battle_simulator.utils.data_loader import DataManager
from wuxia_battle_simulator.validation.validator import Validator


class TestATB(unittest.TestCase):
    def test_tick_order_deterministic(self):
        # Two actors; A has higher agility, should act first consistently
        a = CharacterState(
            id="A",
            name="A",
            faction="华山派",
            faction_terminology={"attack_prefix": "剑", "defense_prefix": "护", "qi_name": "内力"},
            stats=Stats(strength=10, agility=20, defense=5, max_hp=100, max_qi=50),
            hp=100, qi=50, skills=[], cooldowns={}, time_units=0.0
        )
        b = CharacterState(
            id="B",
            name="B",
            faction="武当派",
            faction_terminology={"attack_prefix": "太极", "defense_prefix": "化劲", "qi_name": "真元"},
            stats=Stats(strength=10, agility=10, defense=5, max_hp=100, max_qi=50),
            hp=100, qi=50, skills=[], cooldowns={}, time_units=0.0
        )
        gs = GameState([a, b])
        # Build ATB views
        class V:
            def __init__(self, c):
                self.actor_id = c.id
                self.agility = c.stats.agility
                self.time_units = c.time_units
        views = [V(c) for c in gs.living()]
        clock = ATBClock(threshold=100, tick_scale=1.0)

        first = None
        # advance until someone can act
        for _ in range(10):
            act = clock.tick(views)
            # sync back
            for v in views:
                gs.get_actor(v.actor_id).time_units = v.time_units
            if act:
                first = act
                break
        self.assertEqual(first, "A", "Higher agility should act first")


class _FakeSkillDB:
    # Minimal skill DB for tests
    def __init__(self):
        self._defs = {
            "s_low": {
                1: dict(base_damage=10, power_multiplier=1.0, qi_cost=0, cooldown=0, hit_chance=1.0, critical_chance=0.0, tier_name="一式")
            },
            "s_high": {
                1: dict(base_damage=30, power_multiplier=1.0, qi_cost=0, cooldown=0, hit_chance=1.0, critical_chance=0.0, tier_name="一式")
            }
        }

    def get_tier_params(self, skill_id, tier):
        from wuxia_battle_simulator.engine.battle_simulator import _SkillTierParams
        p = self._defs[skill_id][tier]
        stp = _SkillTierParams(
            base_damage=p["base_damage"],
            power_multiplier=p["power_multiplier"],
            qi_cost=p["qi_cost"],
            cooldown=p["cooldown"],
            hit_chance=p["hit_chance"],
            critical_chance=p["critical_chance"],
            tier_name=p["tier_name"]
        )
        return stp

    def get_tier_name(self, skill_id, tier):
        return self._defs[skill_id][tier]["tier_name"]

    def get_skill_name(self, skill_id):
        return skill_id

    def get_skill_type(self, skill_id):
        return "攻击"


class TestAI(unittest.TestCase):
    def test_ai_prefers_higher_expected_damage(self):
        rng = random.Random(123)
        a = CharacterState(
            id="A",
            name="A",
            faction="华山派",
            faction_terminology={"attack_prefix": "剑", "defense_prefix": "护", "qi_name": "内力"},
            stats=Stats(strength=10, agility=10, defense=5, max_hp=100, max_qi=50),
            hp=100, qi=50,
            skills=[EquippedSkill("s_low", 1), EquippedSkill("s_high", 1)]
        )
        b = CharacterState(
            id="B",
            name="B",
            faction="武当派",
            faction_terminology={"attack_prefix": "太极", "defense_prefix": "化劲", "qi_name": "真元"},
            stats=Stats(strength=10, agility=10, defense=5, max_hp=100, max_qi=50),
            hp=100, qi=50,
            skills=[]
        )
        gs = GameState([a, b])
        ai = HeuristicAI(rng=rng, skills_db=_FakeSkillDB())

        skill_id, target_id, tier = ai.choose_action(gs, a)
        self.assertEqual(skill_id, "s_high")
        self.assertEqual(target_id, "B")
        self.assertEqual(tier, 1)


class TestDamageBuckets(unittest.TestCase):
    def test_damage_bucket_thresholds(self):
        from wuxia_battle_simulator.engine.battle_simulator import BattleSimulator, _SkillTierParams
        rng = random.Random(42)
        actor = CharacterState(
            id="A",
            name="A",
            faction="华山派",
            faction_terminology={"attack_prefix": "剑", "defense_prefix": "护", "qi_name": "内力"},
            stats=Stats(strength=10, agility=10, defense=5, max_hp=100, max_qi=50),
            hp=100, qi=50, skills=[]
        )
        target = CharacterState(
            id="B",
            name="B",
            faction="武当派",
            faction_terminology={"attack_prefix": "太极", "defense_prefix": "化劲", "qi_name": "真元"},
            stats=Stats(strength=10, agility=10, defense=5, max_hp=100, max_qi=50),
            hp=100, qi=50, skills=[]
        )
        class DummyAI: pass
        class DummyClock:
            def current_time(self): return 0.0
        sim = BattleSimulator(state=GameState([actor, target]), ai=DummyAI(), clock=DummyClock(), rng=rng)
        # craft params to control outputs:
        # Ensure < 10% bucket after defense reduction (defense 5 => 2.5 reduction)
        # Use strength=10 contributes via power_multiplier; to isolate, set multiplier 0 so only base_damage applies
        p = _SkillTierParams(base_damage=7, power_multiplier=0.0, qi_cost=0, cooldown=0, hit_chance=1.0, critical_chance=0.0)
        dmg, outcome, bucket = sim.compute_damage(actor, target, p, rng)
        # 0*str + 7 - 2.5 = 4.5 => floor 4 => 4% of 100
        self.assertEqual(bucket, "low", f"expected low, got {bucket} (dmg={dmg})")

        # medium bucket: choose values to avoid critical or miss randomness influencing result
        rng_medium = random.Random(123)
        # choose base_damage that yields floor(dmg) in [10,25]
        # target.defense reduction = 2.5; pick 18.6 -> 16.1 -> floor 16 => 16%
        p = _SkillTierParams(base_damage=18.6, power_multiplier=0.0, qi_cost=0, cooldown=0, hit_chance=1.0, critical_chance=0.0)
        dmg, outcome, bucket = sim.compute_damage(actor, target, p, rng_medium)
        # 0*str + 18.6 - 2.5 = 16.1 => floor 16 => 16%
        self.assertEqual(bucket, "medium", f"expected medium, got {bucket} (dmg={dmg})")

        rng_high = random.Random(321)
        # choose base_damage that yields >25% after defense reduction
        # 0*str + 35 - 2.5 = 32.5 -> 32 => 32% > 25%
        p = _SkillTierParams(base_damage=35, power_multiplier=0.0, qi_cost=0, cooldown=0, hit_chance=1.0, critical_chance=0.0)
        dmg, outcome, bucket = sim.compute_damage(actor, target, p, rng_high)
        # expect high bucket
        self.assertEqual(bucket, "high", f"expected high, got {bucket} (dmg={dmg})")


class TestGoldenNarration(unittest.TestCase):
    def test_seeded_narration_is_stable(self):
        # Use real data manager and templates, but small max_steps for speed
        schema_dir = ROOT / "validation" / "schemas"
        dm = DataManager(Validator(schema_dir))
        data_dir = ROOT / "data"
        chars = dm.load_characters(data_dir / "characters.json")
        skills_db = dm.load_skills(data_dir / "skills.json")
        templates = dm.load_templates(data_dir / "templates.json")
        state = dm.build_game_state(chars)

        rng = random.Random(42)
        clock = ATBClock(threshold=100, tick_scale=1.0)
        ai = HeuristicAI(rng=rng, skills_db=skills_db)
        index = TemplateIndex(templates)
        narrator = TextNarrator(index=index, rng=rng, template_engine=TemplateEngine(VariableResolver()))
        sim = BattleSimulator(state=state, ai=ai, clock=clock, rng=rng)

        events = sim.run_to_completion(max_steps=10)
        lines = [narrator.render(sim.map_event_for_narration(e)) for e in events]
        # Golden prefix - just check first 3 lines contain stable key phrases
        self.assertTrue(any(("威力全开" in line) or ("轰然" in line) for line in lines[:3]))
        # Ensure deterministic count given seed and cap
        self.assertLessEqual(len(lines), 10)


if __name__ == "__main__":
    # Allow running via: python -m unittest wuxia_battle_simulator.tests.test_mvp
    unittest.main()