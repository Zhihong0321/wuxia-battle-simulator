# Testing

This guide describes how to validate correctness, determinism, and data contracts in the Wuxia Battle Engine.

Test philosophy
- Deterministic: The same datasets and seed must produce identical outputs.
- Contract-first: Schemas are the source of truth; invalid data must be rejected early.
- Small checks, fast feedback: unit tests for core engine pieces; integration tests for end-to-end flows.

What to test
1) ATB determinism
- Given a set of actors with known agility, ATBClock.tick() must always select the same next actor under a fixed seed and initial state.
- Guarantees:
  - Progress even with low agility (guard loop)
  - Tie-break by (time_units, actor_id)

2) AI action viability
- With fixed RNG and state:
  - AI should never choose a skill lacking qi or on cooldown.
  - Expected damage per (cooldown + 1) heuristic selects the correct skill and target.
- Edge cases:
  - No viable skills -> returns None or safe pass action.

3) Damage computation
- Unit tests for compute_damage with:
  - hit/miss boundaries at 0 and 1
  - crit probability boundaries
  - bucket labeling (low/medium/high) consistent with configured thresholds

4) GameState transitions
- Apply damage floors at 0; HP never negative.
- Cooldown decrement at turn start; cooldown setting after use; qi costs applied correctly.

5) Narration mapping
- map_event_for_narration:
  - narrative_type correct for hit, miss, crit
  - Names and tier names resolved via SkillDB lookups
  - damage_amount present and non-negative for hits
  - tier_narrative_template present in context when defined on the skill tier
- TextNarrator:
  - Selection precedence honored: per-tier template > templates.json candidates > default template
  - Default template used if no candidates
  - Critical tag 【暴击！】 appended once when context.critical is true
  - TemplateEngine resolves {dot.paths} and logs missing variables gracefully

6) Schema validation
- Positive cases:
  - Valid characters (full stats: hp, max_hp, qi, max_qi, strength, agility, defense), skills (tiers with parameters and narrative_template), templates, config pass.
- Negative cases:
  - characters: negative stats or hp > max_hp rejected
  - skills: missing narrative_template in any tier; parameters not nested; out-of-range hit/crit; non-integer base_damage; rejected
  - templates: invalid comparator or missing fields rejected
  - config: missing rng_seed rejected if required

7) GUI integration (smoke)
- Load data dir with sample datasets
- Select one character for each team, set seed, click Run:
  - Finish mode prints all narration and a final result line
  - Progressive mode prints lines over time and updates HP status between lines
- Editors:
  - Characters: edit full stats and equipped skills; Save to JSON validates and persists
  - Skills: edit tiers via grid, including narrative_template modal; Save to JSON validates, persists, and reloads SkillDB

Deterministic replay checks
- After editing data (but keeping the same seed and unchanged teams), rerun and verify:
  - If data is unchanged, narration lines and winner remain identical.
  - If only per-tier narrative_template text changes, engine outcomes are unchanged; only narration strings differ while event sequence and winner remain identical.

Suggested structure
- tests/
  - engine/test_battle_engine.py
  - engine/processors/test_atb_processor.py
  - engine/processors/test_ai_processor.py
  - engine/processors/test_damage_processor.py
  - engine/processors/test_state_processor.py
  - engine/test_processor_pipeline.py
  - engine/test_battle_context.py
  - narrator/test_mapping.py
  - narrator/test_templates.py
  - narrator/test_precedence.py
  - data/test_schemas.py
  - ui/test_smoke.py (optional; can be an integration script rather than automated test)

Golden scenarios
- Include a sample seed (e.g., 42) and a pair of teams in docs or tests so contributors can run a quick regression and compare outputs (narration lines and winner).

Running tests
- If using pytest:
  - pip install pytest
  - pytest -q

Notes for contributors
- When changing any engine, AI, or mapping logic, update tests accordingly and include a rationale in PR description.
- For non-deterministic failures:
  - Ensure all randomness uses the single RNG instance passed through constructors.
  - Check that any iteration over dicts uses stable ordering or explicit sorting.