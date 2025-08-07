# Data Schemas

All datasets are validated with JSON Schema (Draft 2020-12) at load-time and prior to persistence from the editors. This ensures stable contracts for engine, narrator, and UI.

Files
- characters.json
- skills.json
- templates.json
- config.json

characters.json
- Top-level: either an object with { "characters": [...] } or a raw array [...]
- Character object:
  - id: string (unique)
  - name: string (display)
  - faction: string (optional)
  - stats: object
    - hp: integer >= 1
    - qi: integer >= 0
    - agility: integer >= 0
  - skills: array of equipped skills
    - { "skill_id": string, "tier": integer >= 1 }
- Notes:
  - GUI injects a default placeholder basic_strike tier 1 for characters with no skills when running simulation, but this is only a runtime safety net. Prefer providing at least one valid skill.

skills.json
- Top-level: either an object with { "skills": [...] } or a raw array [...]
- Skill object:
  - id: string (unique)
  - name: string
  - type: string (Chinese labels supported, e.g., 攻击; additional types can be added by schema update)
  - tiers: array of tier objects
    - tier: integer >= 1
    - base_damage: number >= 0
    - power_multiplier: number (optional; defaults used in engine if absent)
    - hit_chance: number in [0, 1]
    - crit_chance: number in [0, 1]
    - qi_cost: integer >= 0
    - cooldown: integer >= 0
- Runtime:
  - DataManager builds a SkillDB for fast lookups by (skill_id, tier), returning a SkillTier with typed fields.

templates.json
- Top-level: either an object with { "templates": [...] } or a raw array [...]
- Template object:
  - id: string
  - narrative_type: string, expected values like:
    - 攻击, 闪避, 抵挡, 暴击 (MVP)
  - template or text: string with placeholders, e.g., {attacker}使出【{skill}】{tier_name}，攻向{target}！
  - conditions: object (optional), simple equality matches against narration context
  - connective_phrases: array of strings (optional)
- Selection:
  - TextNarrator calls TemplateIndex.select(narrative_type, context) -> candidates
  - MVP wraps the list into a simple select() that filters by narrative_type and conditions.

config.json
- rng_seed: integer (default seed used in GUI)
- atb_threshold: integer (e.g., 100)
- atb_tick_scale: number (e.g., 1.0)
- ui: object (optional) for future UI defaults

Validation behavior
- The Validator supports either a named-key payload or a raw array form per dataset.
- Errors present clear paths; minimum/maximum constraints ensure data sanity.
- Editors validate before saving to disk. If invalid, the save is rejected with detailed errors.

Example fragments

characters.json
{
  "characters": [
    {
      "id": "li_san",
      "name": "李三",
      "faction": "牛山派",
      "stats": { "hp": 120, "qi": 80, "agility": 12 },
      "skills": [
        { "skill_id": "basic_strike", "tier": 1 }
      ]
    }
  ]
}

skills.json
{
  "skills": [
    {
      "id": "basic_strike",
      "name": "基础招式",
      "type": "攻击",
      "tiers": [
        { "tier": 1, "base_damage": 20, "hit_chance": 0.9, "crit_chance": 0.1, "qi_cost": 0, "cooldown": 0 }
      ]
    }
  ]
}

templates.json
{
  "templates": [
    {
      "id": "atk_basic",
      "narrative_type": "攻击",
      "template": "{attacker}使出【{skill}】{tier_name}，攻向{target}！",
      "conditions": { "hit": true },
      "connective_phrases": ["刹那间", "说时迟那时快"]
    }
  ]
}

config.json
{
  "rng_seed": 42,
  "atb_threshold": 100,
  "atb_tick_scale": 1.0,
  "ui": {}
}