# Engine: ATB, Battle Processor Pipeline, AI, GameState

This document describes the combat engine: timing model, modular battle processing pipeline, state management, action selection, damage calculation, and event emission.

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

Battle Processor Pipeline
- Constructor: BattleEngine(state, ai, clock, rng, processor_registry).
- Modular Architecture:
  - BattleContext: Carries all battle data through the processing pipeline (state, current actor, action, damage results, events, etc.)
  - StepProcessor Interface: Common interface for all battle processing steps with process(context) method
  - ProcessorPipeline: Executes registered processors in sequence, handling errors and conditional execution
  - ProcessorRegistry: Manages processor configuration and allows runtime modification of the pipeline

- Core Processors:
  1. ATBProcessor: Syncs ATB clock and selects next actor
  2. AIDecisionProcessor: Asks AI to choose action (skill_id, target_id, tier)
  3. ResourceValidationProcessor: Validates qi costs and cooldowns
  4. MovementSkillProcessor: Handles target's movement/dodge skills (miss_chance, partial_miss)
  5. DefenseSkillProcessor: Handles target's defense skills (damage reduction, counter-attacks)
  6. DamageCalculationProcessor: Computes final damage with hit/miss, critical hits, damage buckets
  7. StateUpdateProcessor: Updates HP, qi, cooldowns, and game state
  8. EventGenerationProcessor: Creates BattleEvent objects for narration

- step(): Executes the processor pipeline with current BattleContext, returns List[BattleEvent]
- run_to_completion(): Loop step() until is_battle_over() returns True or max-iteration guard trips
- map_event_for_narration(ev): Returns a context dict used by Narrator (unchanged interface)

- Processor Modification Guidelines:
  - To add new battle mechanics: Create new processor implementing StepProcessor interface
  - To modify battle flow: Update ProcessorRegistry configuration
  - To disable features: Remove processor from registry or add conditional logic
  - To debug: Enable processor-level logging and use BattleContext.processing_log

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