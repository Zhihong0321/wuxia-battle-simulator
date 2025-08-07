import sys
from pathlib import Path
import unittest
import random

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

from wuxia_battle_simulator.engine.atb_system import ATBClock
from wuxia_battle_simulator.engine.game_state import Stats, EquippedSkill, CharacterState, GameState
from wuxia_battle_simulator.engine.ai_policy import HeuristicAI
from wuxia_battle_simulator.narrator.template_index import TemplateIndex
from wuxia_battle_simulator.narrator.variable_resolver import VariableResolver
from wuxia_battle_simulator.utils.template_engine import TemplateEngine


class TestATBTieBreak(unittest.TestCase):
    def test_tie_break_by_actor_id_when_equal(self):
        # Prepare two actors with equal agility and time_units
        a = CharacterState(
            id="A", name="A", faction="华山派",
            faction_terminology={"attack_prefix": "剑", "defense_prefix": "护", "qi_name": "内力"},
            stats=Stats(strength=10, agility=10, defense=5, max_hp=100, max_qi=50),
            hp=100, qi=50, skills=[], cooldowns={}, time_units=50.0
        )
        b = CharacterState(
            id="B", name="B", faction="武当派",
            faction_terminology={"attack_prefix": "太极", "defense_prefix": "化劲", "qi_name": "真元"},
            stats=Stats(strength=10, agility=10, defense=5, max_hp=100, max_qi=50),
            hp=100, qi=50, skills=[], cooldowns={}, time_units=50.0
        )
        gs = GameState([a, b])

        class V:
            def __init__(self, c):
                self.actor_id = c.id
                self.agility = c.stats.agility
                self.time_units = c.time_units

        views = [V(c) for c in gs.living()]
        clock = ATBClock(threshold=100, tick_scale=5.0)  # one tick should ready both

        act = clock.tick(views)
        # Sync back times
        for v in views:
            gs.get_actor(v.actor_id).time_units = v.time_units

        # Expect deterministic tie-break to the lexicographically smaller id "A"
        self.assertEqual(act, "A")


class _FakeSkillDB:
    def __init__(self):
        self._defs = {
            "cheap": {1: dict(base_damage=10, power_multiplier=1.0, qi_cost=0, cooldown=0, hit_chance=1.0, critical_chance=0.0, tier_name="初式")},
            "expensive": {1: dict(base_damage=25, power_multiplier=1.0, qi_cost=30, cooldown=0, hit_chance=1.0, critical_chance=0.0, tier_name="二式")},
            "cooldown": {1: dict(base_damage=20, power_multiplier=1.0, qi_cost=0, cooldown=2, hit_chance=1.0, critical_chance=0.0, tier_name="三式")},
        }

    def get_tier_params(self, skill_id, tier):
        from wuxia_battle_simulator.engine.battle_simulator import _SkillTierParams
        p = self._defs[skill_id][tier]
        return _SkillTierParams(
            base_damage=p["base_damage"],
            power_multiplier=p["power_multiplier"],
            qi_cost=p["qi_cost"],
            cooldown=p["cooldown"],
            hit_chance=p["hit_chance"],
            critical_chance=p["critical_chance"],
            tier_name=p["tier_name"],
        )

    def get_tier_name(self, skill_id, tier):
        return self._defs[skill_id][tier]["tier_name"]

    def get_skill_name(self, skill_id):
        return skill_id

    def get_skill_type(self, skill_id):
        return "攻击"


class TestAIConstraintsAndTargeting(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(7)
        self.skills_db = _FakeSkillDB()

    def test_ai_respects_qi_and_cooldown_filters(self):
        actor = CharacterState(
            id="A", name="A", faction="华山派",
            faction_terminology={"attack_prefix": "剑", "defense_prefix": "护", "qi_name": "内力"},
            stats=Stats(strength=10, agility=10, defense=5, max_hp=100, max_qi=20),  # qi not enough for 'expensive'
            hp=100, qi=20,
            skills=[EquippedSkill("cheap", 1), EquippedSkill("expensive", 1), EquippedSkill("cooldown", 1)],
            cooldowns={"cooldown": 1}  # still on cooldown
        )
        enemy = CharacterState(
            id="E", name="E", faction="武当派",
            faction_terminology={"attack_prefix": "太极", "defense_prefix": "化劲", "qi_name": "真元"},
            stats=Stats(strength=10, agility=10, defense=5, max_hp=100, max_qi=50),
            hp=100, qi=50, skills=[]
        )
        gs = GameState([actor, enemy])
        ai = HeuristicAI(rng=self.rng, skills_db=self.skills_db)

        skill_id, target_id, tier = ai.choose_action(gs, actor)
        self.assertEqual(skill_id, "cheap")
        self.assertEqual(target_id, "E")
        self.assertEqual(tier, 1)

    def test_ai_targets_lowest_hp_enemy(self):
        actor = CharacterState(
            id="A", name="A", faction="华山派",
            faction_terminology={"attack_prefix": "剑", "defense_prefix": "护", "qi_name": "内力"},
            stats=Stats(strength=10, agility=10, defense=5, max_hp=100, max_qi=50),
            hp=100, qi=50,
            skills=[EquippedSkill("cheap", 1)]
        )
        e1 = CharacterState(
            id="E1", name="E1", faction="武当派",
            faction_terminology={"attack_prefix": "太极", "defense_prefix": "化劲", "qi_name": "真元"},
            stats=Stats(strength=10, agility=10, defense=5, max_hp=100, max_qi=50),
            hp=40, qi=50, skills=[]
        )
        e2 = CharacterState(
            id="E2", name="E2", faction="武当派",
            faction_terminology={"attack_prefix": "太极", "defense_prefix": "化劲", "qi_name": "真元"},
            stats=Stats(strength=10, agility=10, defense=5, max_hp=100, max_qi=50),
            hp=30, qi=50, skills=[]
        )
        gs = GameState([actor, e1, e2])
        ai = HeuristicAI(rng=self.rng, skills_db=self.skills_db)

        skill_id, target_id, tier = ai.choose_action(gs, actor)
        self.assertEqual(skill_id, "cheap")
        self.assertEqual(target_id, "E2")  # lowest HP target
        self.assertEqual(tier, 1)


class TestTemplateIndexBoundaries(unittest.TestCase):
    def setUp(self):
        # Minimal templates array with boundary conditions and faction filters
        self.templates = [
            # Hit, non-crit, low boundary just below 10
            {"narrative_type": "attack", "conditions": {"hit": True, "critical": False, "damage_percent": "<10"}, "text": "低伤{actor.name}->{target.name}"},
            {"narrative_type": "attack", "conditions": {"hit": True, "critical": False, "damage_percent": ">=10"}, "text": "中高伤{actor.name}->{target.name}"},
            {"narrative_type": "critical", "conditions": {"critical": True}, "text": "暴击! {actor.name}"},
            {"narrative_type": "attack", "conditions": {"actor_faction": "华山派"}, "text": "华山风格"},
            {"narrative_type": "attack", "conditions": {"actor_faction": "武当派"}, "text": "武当风格"},
            {"narrative_type": "dodge", "conditions": {"hit": False}, "text": "被闪避"},
        ]
        self.index = TemplateIndex(self.templates)

    def test_damage_percent_thresholds(self):
        # Simulate selection by filtering via TemplateIndex API:
        # Using private behavior through public select: provide narrative_type and condition dict
        from types import SimpleNamespace
        ctx_low_9_9 = {"narrative_type": "attack", "hit": True, "critical": False, "damage_percent": 9.9, "actor_faction": "华山派", "target_faction": "武当派", "actor": {"name": "A"}, "target": {"name": "B"}}
        ctx_low_10 = {"narrative_type": "attack", "hit": True, "critical": False, "damage_percent": 10.0, "actor_faction": "华山派", "target_faction": "武当派", "actor": {"name": "A"}, "target": {"name": "B"}}

        cands_9_9 = self.index.select(ctx_low_9_9["narrative_type"], ctx_low_9_9)
        texts_9_9 = [t["text"] for t in cands_9_9]
        self.assertIn("低伤{actor.name}->{target.name}", texts_9_9)

        cands_10 = self.index.select(ctx_low_10["narrative_type"], ctx_low_10)
        texts_10 = [t["text"] for t in cands_10]
        self.assertIn("中高伤{actor.name}->{target.name}", texts_10)

    def test_faction_filters(self):
        ctx_huashan = {"narrative_type": "attack", "actor_faction": "华山派", "hit": True, "critical": False}
        ctx_wudang = {"narrative_type": "attack", "actor_faction": "武当派", "hit": True, "critical": False}

        t_h = [t["text"] for t in self.index.select("attack", ctx_huashan)]
        t_w = [t["text"] for t in self.index.select("attack", ctx_wudang)]
        self.assertIn("华山风格", t_h)
        self.assertIn("武当风格", t_w)

    def test_dodge_condition(self):
        ctx_dodge = {"narrative_type": "dodge", "hit": False}
        t = [t["text"] for t in self.index.select("dodge", ctx_dodge)]
        self.assertIn("被闪避", t)


class TestVariableResolverRobustness(unittest.TestCase):
    def setUp(self):
        self.resolver = VariableResolver()
        self.engine = TemplateEngine(self.resolver)

    def test_missing_keys_yield_empty(self):
        text = "Hello {actor.name} {missing.key}"
        ctx = {"actor": {"name": "A"}}
        out = self.engine.render(text, ctx)
        self.assertEqual(out, "Hello A ")

    def test_list_index_and_oob(self):
        text = "{arr[0]}-{arr[2]}-{arr[10]}"
        ctx = {"arr": ["x", "y", "z"]}
        out = self.engine.render(text, ctx)
        self.assertEqual(out, "x-z-")

    def test_nested_mix(self):
        text = "{actor.skills[1].name}"
        ctx = {"actor": {"skills": [{"name": "s1"}, {"name": "s2"}]}}
        out = self.engine.render(text, ctx)
        self.assertEqual(out, "s2")


if __name__ == "__main__":
    unittest.main()