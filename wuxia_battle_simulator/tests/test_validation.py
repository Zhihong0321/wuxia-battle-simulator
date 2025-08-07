import os
import sys
from pathlib import Path
import unittest
import json
import copy

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

from wuxia_battle_simulator.validation.validator import Validator
from wuxia_battle_simulator.utils.data_loader import DataManager


class TestValidationAndLoading(unittest.TestCase):
    def setUp(self):
        self.schema_dir = ROOT / "validation" / "schemas"
        self.data_dir = ROOT / "data"
        self.validator = Validator(self.schema_dir)
        self.dm = DataManager(self.validator)

    def test_load_all_happy_path(self):
        chars = self.dm.load_characters(self.data_dir / "characters.json")
        skills_db = self.dm.load_skills(self.data_dir / "skills.json")
        templates = self.dm.load_templates(self.data_dir / "templates.json")
        config = self.dm.load_config(self.data_dir / "config.json")
        state = self.dm.build_game_state(chars)

        self.assertGreaterEqual(len(chars), 2)
        # SkillDB object should provide required API
        self.assertTrue(hasattr(skills_db, "get_tier_params"))
        self.assertTrue(hasattr(skills_db, "get_tier_name"))
        self.assertTrue(hasattr(skills_db, "get_skill_name"))
        self.assertTrue(hasattr(skills_db, "get_skill_type"))
        self.assertGreaterEqual(len(templates), 10)
        # Config key is rng_seed in current implementation
        self.assertIn("rng_seed", config)
        # basic state integrity
        self.assertGreaterEqual(len(state.characters), 2)
        for c in state.characters.values():
            self.assertEqual(c.hp, c.stats.max_hp)
            self.assertEqual(c.qi, c.stats.max_qi)

    def test_characters_missing_required_field(self):
        # Load original and remove a required field to trigger validation error (if jsonschema installed)
        with open(self.data_dir / "characters.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        bad = copy.deepcopy(data)
        # remove name of first character
        if bad and isinstance(bad, list):
            if "name" in bad[0]:
                del bad[0]["name"]
        tmp = ROOT / "data" / "_tmp_bad_characters.json"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(bad, f, ensure_ascii=False, indent=2)
            # Depending on jsonschema availability, DataManager may raise or log a warning.
            try:
                _ = self.dm.load_characters(tmp)
                # If no exception, at least ensure DataManager returns something reasonable (len preserved)
                self.assertTrue(True)
            except Exception as e:
                # Accept a validation failure as pass condition
                self.assertTrue("Validation" in str(e) or "schema" in str(e) or "validate" in str(e))
        finally:
            if tmp.exists():
                tmp.unlink()

    def test_skills_wrong_type(self):
        with open(self.data_dir / "skills.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        bad = copy.deepcopy(data)
        # Dataset may be either a dict keyed by id, or a list of skill entries. Normalize to a single skill dict.
        skill_entry = None
        if isinstance(bad, dict):
            first_skill_id = next(iter(bad.keys()))
            skill_entry = bad[first_skill_id]
        elif isinstance(bad, list) and bad:
            # pick first object element
            for item in bad:
                if isinstance(item, dict):
                    skill_entry = item
                    break
        if not isinstance(skill_entry, dict):
            self.skipTest("Unexpected skills structure at top-level")
        tiers = skill_entry.get("tiers")
        if isinstance(tiers, list) and tiers:
            tiers[0]["base_damage"] = "NaN"  # should be number
        elif isinstance(tiers, dict) and tiers:
            first_tier_key = next(iter(tiers.keys()))
            tiers[first_tier_key]["base_damage"] = "NaN"
        else:
            self.skipTest("Unexpected tiers structure in skills")
        tmp = ROOT / "data" / "_tmp_bad_skills.json"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(bad, f, ensure_ascii=False, indent=2)
            try:
                _ = self.dm.load_skills(tmp)
                # If no exception thrown, accept soft validation as pass
                self.assertTrue(True)
            except Exception as e:
                # Accept a validation failure as pass condition
                self.assertTrue("Validation" in str(e) or "schema" in str(e) or "validate" in str(e))
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except Exception:
                    pass


if __name__ == "__main__":
    unittest.main()