# Narrator: Templates, Rendering, Progressive Mode

This document explains the narration pipeline: how events map to Chinese text, the template system, per-tier template precedence, and the GUI’s Finish vs Progressive playback modes.

Goals
- Human-readable Chinese narration generated from structured battle events
- Deterministic template selection with seeded RNG
- Template-driven assembly so writers can control style without touching engine code
- Two playback modes for UX: all-at-once and progressive

Data flow
1) BattleSimulator emits BattleEvent objects with enough detail (attacker, target, skill, tier, hit/crit, damage, buckets).
2) simulator.map_event_for_narration(ev) converts BattleEvent into a context dict, including:
   - narrative_type: 攻击, 闪避, 抵挡, 暴击
   - names: attacker, target, skill, tier_name
   - flags: hit, critical
   - damage_amount and damage_percent (bucket)
   - tier_narrative_template: per-tier template text (if present in the SkillDB for the skill/tier)
3) TextNarrator.render(context) selects a template and renders final Chinese text.

Template selection
- TextNarrator depends on a TemplateIndex providing:
  - select(narrative_type, context) -> list of candidate templates
- MVP GUI wraps the templates list via a simple adapter class with a select() method that:
  - Filters by narrative_type == template["narrative_type"]
  - Applies simple conditions: all key=value pairs must match context
- Selection precedence (attack events):
  1) If context.tier_narrative_template is present, use it directly for rendering (highest priority).
  2) Else, query TemplateIndex for candidates and pick deterministically (seeded RNG).
  3) Else, fall back to get_default_template() per narrative_type.
- Determinism:
  - Given the same RNG seed and event sequence, selection is reproducible. Using a per-tier template bypasses randomness and remains deterministic.

Critical tag behavior
- After rendering the base text, if context.critical is true, TextNarrator appends the fixed tag 【暴击！】 once at the end of the line.
- The GUI may additionally append a damage suffix “（伤害: X）” where X is damage_amount/hp_delta when available.

Template Rendering
- utils.TemplateEngine + narrator.VariableResolver:
  - Supports {dot.path} notation and array indexing {arr[0]}
  - Missing variables resolve to "" and are logged at debug level
- TextNarrator may add a connective phrase prefix（随即，说时迟那时快，…）with some probability for flow.

Finish vs Progressive mode (GUI)
- Finish mode:
  - The simulator runs to completion; all events are rendered immediately into the commentary box.
- Progressive mode:
  - The simulator still computes the full event list deterministically.
  - The GUI schedules each narration line with Tk after() according to the user-configured delay (default 0.5s per event).
  - The HP status lines for Team A/B update after each scheduled event to visualize health changes over time.

Damage visibility
- Even if templates do not include damage directly, the GUI appends a suffix “（伤害: X）” to each rendered line whenever the context contains damage_amount/hp_delta/damage.

Extending narration
- Add new narrative_type values (e.g., 治疗, 增益, 减益) and define corresponding templates.
- Expand conditions to support ranges or more complex predicates (e.g., damage_percent == "high" and critical == true).
- Implement a richer TemplateIndex to index by narrative_type and pre-compile conditions.
- Add localized template sets for stylistic variety (e.g., school-specific phrasing).