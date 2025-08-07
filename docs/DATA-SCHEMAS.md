# Data Schemas

All datasets are validated with JSON Schema (Draft-07) at load-time and prior to persistence from the editors. This ensures stable contracts for engine, narrator, and UI. Note: Some reference documentation may mention Draft 2020-12; the runtime validator targets Draft-07 semantics.

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
  - stats: object (REQUIRED)
    - hp: integer >= 1
    - max_hp: integer >= hp
    - qi: integer >= 0
    - max_qi: integer >= qi
    - strength: integer >= 0
    - agility: integer >= 0
    - defense: integer >= 0
  - skills: array of equipped skills
    - { "skill_id": string, "tier": integer >= 1 }
- Notes:
  - GUI may inject a default placeholder basic_strike tier 1 for characters with no skills at runtime, but this is only a safety net. Prefer providing at least one valid skill with an allowed tier.

skills.json
- Top-level: either an object with { "skills": [...] } or a raw array [...]
- Skill object:
  - id: string (unique)
  - name: string
  - type: string (Chinese labels supported, e.g., 攻击; additional types can be added by schema update)
  - tiers: array of tier objects
    - tier: integer >= 1
    - tier_name: string
    - parameters: object (REQUIRED)
      - base_damage: integer >= 0
      - power_multiplier: number >= 0
      - hit_chance: number in [0, 1]
      - critical_chance: number in [0, 1]
      - qi_cost: integer >= 0
      - cooldown: integer >= 0
    - visual_effects: string[] (optional)
    - sound_effects: string[] (optional)
    - narrative_template: string (REQUIRED) — per-skill, per-tier Chinese narration template. Variables resolved via TemplateEngine (e.g., {attacker}, {target}, {skill}, {tier_name}). If the attack is critical, the narrator appends a fixed tag 【暴击！】 after rendering.
- Runtime:
  - DataManager builds a SkillDB for fast lookups by (skill_id, tier), returning a SkillTier with typed fields and the narrative_template exposed to the narrator via map_event_for_narration context as tier_narrative_template.

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
  - The MVP adapter filters by narrative_type and conditions.
  - Attack narration prefers the per-tier narrative_template from skills.json when present; otherwise falls back to templates.json candidates, then a built-in default.

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
      "stats": {
        "hp": 120,
        "max_hp": 120,
        "qi": 80,
        "max_qi": 100,
        "strength": 14,
        "agility": 12,
        "defense": 6
      },
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
      "id": "huashan_sword",
      "name": "华山剑法",
      "type": "攻击",
      "tiers": [
        {
          "tier": 1,
          "tier_name": "起手式",
          "parameters": {
            "base_damage": 16,
            "power_multiplier": 0.9,
            "qi_cost": 8,
            "cooldown": 1,
            "hit_chance": 0.82,
            "critical_chance": 0.10
          },
          "visual_effects": ["剑光"],
          "sound_effects": ["破空声"],
          "narrative_template": "{attacker}运剑如风，【{skill}】{tier_name}刺向{target}！"
        },
        {
          "tier": 2,
          "tier_name": "精进式",
          "parameters": {
            "base_damage": 24,
            "power_multiplier": 1.1,
            "qi_cost": 12,
            "cooldown": 1,
            "hit_chance": 0.85,
            "critical_chance": 0.15
          },
          "visual_effects": ["剑光", "寒芒"],
          "sound_effects": ["破空声"],
          "narrative_template": "{attacker}怒喝一声，【{skill}】{tier_name}威力全开，剑光撕裂空气，重创{target}！"
        }
      ]
    }
  ]
}

templates.json
- Still supported for global fallback and non-attack events; attack narration now prefers per-tier narrative_template when available.
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