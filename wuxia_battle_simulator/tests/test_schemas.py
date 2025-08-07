import json
import os
import unittest

from wuxia_battle_simulator.validation.validator import Validator


DATA_DIR = os.path.join("wuxia_battle_simulator", "data")
SCHEMA_DIR = os.path.join("wuxia_battle_simulator", "schemas")


class TestJSONSchemas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validator = Validator(schema_dir=SCHEMA_DIR)
        cls.validator.load_schemas()

    def _load_json(self, relpath: str):
        full = os.path.join(DATA_DIR, relpath)
        with open(full, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_characters_schema_happy_path(self):
        data = self._load_json("characters.json")
        # Should not raise
        self.validator.validate("characters", data)

    def test_skills_schema_happy_path(self):
        data = self._load_json("skills.json")
        # Should not raise (supports array or object map, tiers as array or object)
        self.validator.validate("skills", data)

    def test_templates_schema_happy_path(self):
        data = self._load_json("templates.json")
        # Should not raise (conditions keys optional, comparator or enum for damage_percent)
        self.validator.validate("templates", data)

    def test_config_schema_happy_path(self):
        data = self._load_json("config.json")
        # Should not raise (requires rng_seed)
        self.validator.validate("config", data)

    def test_config_schema_missing_seed_raises(self):
        # Build minimal invalid config (missing rng_seed)
        bad = {}
        with self.assertRaises(ValueError):
            self.validator.validate("config", bad)

    def test_template_schema_invalid_damage_percent_raises(self):
        # invalid damage_percent comparator string
        bad_templates = [
            {
                "id": "t-invalid",
                "narrative_type": "attack",
                "text": "invalid comparator",
                "conditions": {
                    "damage_percent": ">> 10"  # invalid comparator
                }
            }
        ]
        with self.assertRaises(ValueError):
            self.validator.validate("templates", bad_templates)

    def test_skills_schema_invalid_type_raises(self):
        bad_skills = [
            {
                "id": "s1",
                "name": "BadSkill",
                "type": "healing",  # not in enum
                "tiers": [
                    {
                        "base_damage": 1,
                        "power_multiplier": 0.0,
                        "qi_cost": 0,
                        "cooldown": 0,
                        "hit_chance": 1.0,
                        "critical_chance": 0.0
                    }
                ]
            }
        ]
        with self.assertRaises(ValueError):
            self.validator.validate("skills", bad_skills)

    def test_characters_schema_negative_stats_raises(self):
        bad_chars = [
            {
                "id": "c1",
                "name": "BadGuy",
                "faction": "魔宗",
                "max_hp": 100,
                "strength": -1,  # invalid
                "defense": 0,
                "agility": 0,
                "qi": 0,
                "skills": []
            }
        ]
        with self.assertRaises(ValueError):
            self.validator.validate("characters", bad_chars)


if __name__ == "__main__":
    unittest.main()