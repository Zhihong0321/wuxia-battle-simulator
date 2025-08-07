# Contributing Guide

This project is designed so humans and AI agents can collaborate safely and productively. Follow these guidelines to keep the system deterministic, testable, and easy to extend.

Principles
- Determinism first: Same inputs (datasets + seed) must produce the same outputs.
- Contracts over code: Changes to data contracts (schemas) require clear docs and tests.
- Small, reviewable diffs: Prefer incremental PRs with tight scope.
- Observable behavior: Add logging where helpful; avoid noisy logs in hot loops.
- Backward compatibility: Avoid breaking the GUI or data formats unintentionally.

Repository structure
- wuxia_battle_simulator/
  - engine/: ATBClock, BattleEngine with processor pipeline, GameState, AI
  - narrator/: TextNarrator, VariableResolver
  - utils/: DataManager, TemplateEngine, logger
  - validation/: schemas and Validator
  - ui/: Tkinter GUI and editors
- docs/: Documentation suite
- tests/ (recommended): Determinism, schema, and integration tests

Developer setup
- Python 3.10+
- Optional: create venv
- Install dependencies (if requirements.txt exists): pip install -r requirements.txt
- Run GUI: python -m wuxia_battle_simulator.ui.run_ui

Coding standards
- Python style: PEP 8 (reasonable line lengths); type hints for public APIs
- Names: Prefer explicit names over abbreviations in public interfaces
- Logging: Use utils.logger.get_logger(); debug logs for template resolution and data issues
- Errors: Raise clear exceptions in engine/validation; GUI should catch and render user-friendly messages

Data contracts
- All changes to characters.json, skills.json, templates.json, config.json must be reflected in:
  - JSON Schemas under validation/schemas
  - docs/DATA-SCHEMAS.md with examples
  - DataManager/SkillDB to expose required runtime params
- Editors validate before persisting changes; do not bypass validation.

Determinism checklist
- All randomness must use the seeded RNG passed down by the GUI or caller.
- Do not use module-level random.* or time.* based logic in engine/narration.
- Sorting for tie-breaks must be explicit and stable (e.g., by id or name).

Testing
- Add or update tests to cover:
  - ATB determinism with fixed seeds
  - AI action viability (qi/cooldowns)
  - Damage calculation ranges and bucketing
  - Narration context mapping correctness
  - Schema validations (positive/negative cases)
- Recommended structure: tests/engine/, tests/narrator/, tests/data/

Commit and PR process
- Branch naming: feature/short-name, fix/short-name, docs/short-name
- Commit messages: Imperative mood; reference scope and motivation
- PR template (suggested):
  - What/Why
  - Tests
  - Schema/Docs impact
  - Breaking changes?
  - Screenshots (if UI)

Roadmapping and Issues
- Short-term tasks go in docs/ROADMAP.md
- Open issues with clear reproduction steps and seed/datasets used
- Tag issues: engine, narrator, data, schema, ui, docs, test, perf

AI agent guidance
- Always read docs/ARCHITECTURE.md and docs/ENGINE.md before engine changes.
- If a tool error mentions AttributeError or missing methods, verify class APIs in code first.
- Before editing files, search for related definitions across the repo to avoid diverging APIs.
- After making changes, run the GUI locally and capture a deterministic run with seed and selected characters.

Security and safety
- No external network calls in engine or GUI without explicit configuration and docs.
- Do not execute untrusted templates; VariableResolver and TemplateEngine must remain safe (no eval).
- Keep editors restrictive and validated to prevent corrupt datasets.

Recent Changes
- Per-tier narrative templates: Each skill tier now requires narrative_template in skills.json. Narrator prioritizes this over templates.json and appends a fixed 【暴击！】 tag on critical hits.
- Skills Editor overhaul: Replaced free-form tiers text with a Treeview grid. Added validators, inline cell editing, and a modal multiline editor for narrative_template. Save persists immediately and reloads SkillDB.
- Characters Editor fields: Expanded stats to hp, max_hp, qi, max_qi, strength, agility, defense. Saves validate against schema and persist to characters.json.
- Schemas and docs: Updated docs/DATA-SCHEMAS.md, docs/NARRATOR.md, docs/UI.md, docs/TESTING.md to reflect the above; runtime validator targets Draft-07.

License
- Add or update the project license if needed (MIT recommended for open collaboration).

Thanks for contributing!