# Documentation Index

Welcome to the Wuxia Battle Simulator (MVP) documentation. This repository is structured so new contributors and AI agents can quickly understand the architecture, data contracts, and contribution workflow.

Start here:
- ./ARCHITECTURE.md — System overview, modules, and data flow
- ./ENGINE.md — ATB, Simulator, AI policy, and GameState
- ./NARRATOR.md — Narration pipeline, templates, and variable resolution
- ./DATA-SCHEMAS.md — JSON schemas and dataset contract
- ./UI.md — Tkinter GUI, progressive narrator, and editors
- ./TESTING.md — Determinism, validation tests, and guidelines
- ./STYLEGUIDE.md — Python style, logging, error handling
- ./CONTRIBUTING.md — Branching, PR review, code ownership, and roadmapping
- ./ROADMAP.md — MVP goals, near-term tasks, and future directions

Quick start
- Python 3.10+
- Run GUI:
  - python -m wuxia_battle_simulator.ui.run_ui

Project layout
- wuxia_battle_simulator/engine: ATB, battle engine with processor pipeline, AI, game state
- wuxia_battle_simulator/narrator: TextNarrator and variable resolver
- wuxia_battle_simulator/utils: DataManager/loader, TemplateEngine, logger
- wuxia_battle_simulator/validation: JSON Schema validator
- wuxia_battle_simulator/ui: Tkinter GUI (Battle Engine, Editors)
- docs: Documentation suite

Key design choices
- Deterministic simulation driven by seeded RNG
- JSON Schema Draft 2020-12 enforced at load-time and before persistence
- Narrative templates in Chinese with safe variable substitution
- MVP GUI to enable end-to-end validation and iteration