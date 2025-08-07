# Roadmap

This roadmap outlines near-term improvements and longer-term directions for the Wuxia Battle Engine. It is designed to help new contributors and AI agents pick up tasks safely.

Near-term (MVP+)
- Testing and determinism
  - Add a tests/ suite covering ATB determinism, AI viability, damage bucketing, narrator rendering, and schema validations
  - Provide golden seed scenarios for quick regression checks
- UI polish
  - Replace HP status strings with mini HP bars per actor
  - Dual-list team builder with add/remove buttons instead of multi-select listboxes
  - Export battle logs to JSON/Markdown
- Editors
  - Replace tiers text area with a tabular tier editor (per-field validators)
  - Add undo/redo and diff preview before saving
- Data/Schemas
  - Finalize negative-case tests in schemas (invalid types, comparators, missing fields)
  - Add optional fields for traits and resistances with clear engine interpretation
- Engine extensions (safe + incremental)
  - Add new processors for "defend" and "wait" actions; reduce incoming damage or adjust ATB gain
  - Expose per-skill crit multipliers and damage formulas via data
  - Emit structured events for misses, blocks, counters (narration-ready)
  - Add processor configuration options for different battle modes

Mid-term
- Status effects
  - Buffs/debuffs with durations (e.g., attack_up, defense_up, bleed)
  - Schema support and event emission; AI awareness of effects
- Targeting and multi-hit skills
  - Skills that hit multiple targets or chain to new targets
  - AI scoring for AoE vs single-target trade-offs
- Modular AI
  - Strategy profiles per character or faction
  - Pluggable scoring components (threat, synergy, resource management)
- Narration
  - Richer TemplateIndex with compiled conditions and weightings
  - School/faction-specific phrases; hierarchical fallback
  - Localization pipeline (multi-language templates)

Long-term
- Performance and scale
  - Headless simulation mode with batch runs for balance testing
  - Thread pool for AI and/or simulation steps with careful determinism controls
- GUI overhaul
  - Switch to a modern UI toolkit or web-based frontend with richer visuals
  - Animations and real-time HP bars; skill icons and cooldown indicators
- Persistence and tooling
  - Scenario files (teams, seeds, overrides) for reproducible demos
  - Battle replay serialization and deterministic playback

Principles for roadmap execution
- Maintain determinism across changes (single RNG, explicit tie-breaks)
- Schema-first: extend data contracts and update docs before engine changes
- Small, reversible steps: prefer incremental PRs with tests and docs