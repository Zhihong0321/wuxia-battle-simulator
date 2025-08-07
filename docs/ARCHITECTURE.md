# Architecture

This document explains the overall system design of the Wuxia Battle Engine MVP: modules, data flow, determinism guarantees, and key extension points.

High-level goals
- Deterministic, seed-driven simulation for reproducibility
- Strict data contracts enforced via JSON Schema
- Clean separation between engine (simulation) and presentation (narration/UI)
- Extensible AI policy and template-driven narration
- Simple GUI for end-to-end iteration and validation

Module map
- engine
  - atb_system.py: Deterministic ATBClock; accumulates time_units; selects next actor by (time_units, actor_id) tie-break
  - game_state.py: Core runtime types (Stats, EquippedSkill, CharacterState) and GameState orchestration (apply damage, qi, cooldowns; living(); is_battle_over())
  - ai_policy.py: HeuristicAI scoring viable skills; depends on a SkillDB abstraction (provided by DataManager)
  - battle_engine.py: Modular BattleEngine with processor pipeline; BattleContext data flow; StepProcessor interface; ProcessorRegistry configuration
  - processors/: Individual battle processing modules (ATB, AI Decision, Resource Validation, Movement, Defense, Damage, State Update, Event Generation)
- narrator
  - text_narrator.py: TextNarrator with render(context); resolves template candidates via TemplateIndex; uses TemplateEngine + VariableResolver
  - variable_resolver.py: Safe dotted/indexed path resolution for template variables
- utils
  - data_loader.py: DataManager that loads/validates JSON files and builds runtime SkillDB
  - template_engine.py: Lightweight template formatter with missing-var logging; compatible format/render()
  - logger.py: Central logging utility
- validation
  - validator.py: Schema loading and validation (Draft 2020-12)
  - schemas/: JSON schema documents for characters, skills, templates, config
- ui
  - run_ui.py: Tkinter GUI; battle playback; progressive narrator; HP visualization; Character and Skill editors

Key data flows
1) Data load
- App.load_data_dir reads characters.json, skills.json, templates.json, config.json
- Validator validates each dataset against schema
- DataManager builds SkillDB for runtime queries; builds GameState on demand

2) Battle Processing Pipeline
- BattleContext initialized with current game state
- ATBProcessor selects next actor deterministically via ATBClock
- AIDecisionProcessor chooses (skill_id, target_id, tier) using SkillDB and current state
- ResourceValidationProcessor validates qi costs and cooldowns
- MovementSkillProcessor handles target dodge/movement skills (miss_chance, partial_miss)
- DefenseSkillProcessor handles target defense skills (damage reduction, counter-attacks)
- DamageCalculationProcessor computes final damage with crit/miss logic (seeded RNG)
- StateUpdateProcessor applies qi/cooldowns/HP deltas to GameState
- EventGenerationProcessor emits BattleEvent objects for narration
- Pipeline continues until is_battle_over

3) Narration
- BattleEngine.map_event_for_narration(ev) emits a context dict: narrative_type (Chinese), actor/skill/tier names, hit/critical flags, damage bucket and amount
- TextNarrator.render(context) selects a template via TemplateIndex.select() and renders text via TemplateEngine(VariableResolver)

4) GUI
- Builds battle engine from selected characters with default processor configuration
- Finish mode: render all events immediately
- Progressive mode: append one event every N seconds using Tk after()
- Live HP visualization: shows Team A/B names and current/max HP per actor; updated after each event
- Editors: Characters and Skills with JSON persistence and validation

Determinism strategy
- RNG: a single Python random.Random seeded by user input
- ATB: monotonic accumulation with a guard loop to ensure progress; deterministic selection order
- AI: relies only on RNG and current state; no non-deterministic sources
- Narration: template choice uses same RNG; optional prioritized phrase selection remains deterministic via sorted tie-breakers

Extension points
- Battle Processors: add new processors implementing StepProcessor interface for new mechanics (status effects, environmental hazards, etc.)
- AI policies: add new policy classes implementing the same interface
- Skills: extend SkillDB to support additional params (e.g., status effects, area damage)
- Events: emit richer event types (buffs, debuffs, heals) and extend narration mapping
- Processor Configuration: modify ProcessorRegistry to enable/disable features or change battle flow
- Narration: add template conditions and richer resolvers
- UI: add battle logs export, replays, graphical HP bars, animations, processor pipeline visualization