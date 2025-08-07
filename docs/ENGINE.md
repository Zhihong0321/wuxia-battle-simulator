# Engine: ATB, Simulator, AI, GameState

This document describes the combat engine: timing model, state, action selection, damage, and event emission.

Determinism
- Single RNG: A Python random.Random seeded by user input drives all stochastic behavior (hit, crit, narration selection).
- ATB ordering: Deterministic tie-break by (accumulated time_units, actor_id).
- Template selection: Deterministic by RNG, with prioritized phrase selection sorted by template id to keep stable under fixed seeds.

ATBClock
- Purpose: Decide which actor acts next according to agility and a threshold.
- Inputs:
  - threshold: time_units needed to act (default 100 via config)
  - tick_scale: scales agility per tick (configurable)
- Behavior:
  - Accumulate time_units += agility * tick_scale per tick for all living actors.
  - If no actor reaches threshold in a single tick, a guard loop continues ticking until at least one actor is ready (prevents stalls with very low agility).
  - Select the actor with highest time_units; deterministic tie-break by actor_id; consume threshold from that actor's time_units.
- Output:
  - Returns next actor id (or reference) to act.

GameState
- Structures (dataclasses in engine/game_state.py):
  - Stats: hp, qi, agility; may include other attributes in the future.
  - EquippedSkill: { skill_id, tier } per character.
  - CharacterState: name, team marker, Stats, equipped skills, cooldowns map.
- Core methods:
  - actors(): iterator over all CharacterState (stable order).
  - living(): iterator over alive characters (hp > 0).
  - is_battle_over(): True when <= 1 side has living members.
  - apply_damage(target_id, amount): subtract hp (floor at 0).
  - spend_qi(actor_id, cost), set_cooldown(actor_id, skill_id, cd), dec_cooldowns(actor_id): resource and CD management.

Skills and SkillDB
- DataManager.load_skills builds a runtime SkillDB with:
  - SkillDef: id, name, type (Chinese labels supported), tiers[]
  - SkillTier: numeric properties such as base_damage, hit_chance, crit_chance, qi_cost, cooldown, power_multiplier, etc.
- Skill selection at runtime queries SkillDB for a skill_id+tier to fetch parameters.

AI: HeuristicAI
- Objective: Pick a viable action maximizing expected damage per (cooldown + 1), subject to qi and cooldown constraints.
- Steps:
  1. Enumerate equipped skills on the acting character.
  2. Filter viable tiers by available qi and cooldown == 0.
  3. Estimate expected damage with critical and hit probabilities from tier params.
  4. Pick a target (typically the lowest HP opponent).
  5. Return (skill_id, target_id, tier). If none viable, the actor may pass (no-op) and the loop continues.

BattleSimulator
- Constructor: BattleSimulator(state, ai, clock, rng).
- step():
  1. Sync ATB and select next actor.
  2. Turn start: decrement cooldowns for the acting actor.
  3. Ask AI to choose action (skill_id, target_id, tier). If none, produce a no-op event if needed and continue.
  4. Compute damage:
     - Sample hit/miss via hit_chance.
     - If hit, sample critical via crit_chance; apply crit multiplier if present.
     - Apply damage buckets (e.g., high/medium/low) for narration.
     - Deduct qi cost and set cooldown.
     - Update target HP.
  5. Emit a BattleEvent with attacker, target, skill_id, tier, hit/crit flags, damage amount, bucket labels, and any auxiliary data.
- run_to_completion(): Loop step() until is_battle_over() returns True or max-iteration guard trips.
- map_event_for_narration(ev): Returns a context dict used by Narrator. Includes:
  - narrative_type (Chinese label: 攻击/抵挡/闪避/暴击)
  - attacker/target names
  - skill name and tier name (resolved through SkillDB)
  - flags: hit, critical
  - damage_amount, damage_percent (bucket)

Event Model
- BattleEvent fields (typical):
  - actor_id, target_id
  - skill_id, tier
  - hit (bool), critical (bool)
  - damage (int), damage_bucket (string), maybe miss reasons
- The narration mapper resolves human-readable names and narrative_type.

Configuration
- config.json fields typically include:
  - rng_seed (default used by GUI if user-provided seed absent)
  - atb_threshold (e.g., 100)
  - atb_tick_scale (e.g., 1.0)
  - ui: optional UI defaults

Performance and Limits
- MVP is single-threaded and processes a small number of actors.
- Extensions:
  - Parallel AI scoring for many actors (thread pool).
  - Vectorized damage sampling for large-scale sims.
  - Early stop when outcome can be inferred.

Testing Guidelines
- Deterministic ATB: given seed and stats, acting order must be reproducible.
- AI viability: respects qi and cooldown; no invalid skill targets.
- Damage bounds: damage in acceptable ranges and buckets consistent with rules.
- Narration mapping: narrative_type aligns with hit/critical; names resolved via SkillDB.