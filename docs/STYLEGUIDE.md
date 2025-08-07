# Style Guide

This guide codifies conventions for code, data, and documentation to keep the Wuxia Battle Simulator easy to read, extend, and debug.

Coding (Python)
- Version: Target Python 3.10+
- Imports:
  - Absolute imports within the package: from wuxia_battle_simulator.engine.battle_engine import BattleEngine
  - Group stdlib, third-party, then local
- Types:
  - Use type hints for public functions/classes
  - Prefer dataclasses for simple state containers
- Naming:
  - Modules: snake_case
  - Classes: PascalCase
  - Functions/vars: snake_case
  - Constants: UPPER_SNAKE
- Functions:
  - Keep functions small and pure where possible
  - Avoid side effects in helpers unless clearly documented
- Errors:
  - Raise specific exceptions in engine/validation; catch and translate to user-friendly messages at the UI layer
- Logging:
  - Use utils.logger.get_logger()
  - Levels: debug for internal details (template vars, selection), info for startup/major milestones, warning/error for recoverable/non-recoverable problems
- Randomness:
  - Never use random.* at module level; always pass a seeded rng to classes and use that instance
- Ordering:
  - Do not rely on dict ordering for critical logic; sort explicitly or use stable sequences

Engine conventions
- Determinism:
  - Explicit tie-breaks (e.g., by id)
  - Guard loops to ensure progress where needed (ATB accumulation)
- State:
  - Keep GameState as the single source of truth for combat state
  - Avoid duplicating HP/qi/cooldown logic in multiple places
- Events:
  - BattleEvent must contain all data required for narration and analysis
  - Extend via additive fields; avoid breaking existing consumers

Narration conventions
- Template variables:
  - Use simple, descriptive placeholders: {attacker}, {target}, {skill}, {tier_name}
  - Avoid logic in templates; conditions belong in the index/filtering layer
- Selection:
  - Keep template selection deterministic under a fixed RNG; sort candidates for any weighted/tie-breaking behavior
- Safety:
  - VariableResolver must not execute code; it only resolves dotted/indexed paths

UI conventions
- Separation:
  - Keep UI logic (Tk widgets and scheduling) separate from engine logic
  - Call engine/narration through well-defined APIs
- Responsiveness:
  - Use after() for progressive flows; do not busy-wait or sleep in the UI thread
- Editors:
  - Validate before writing to JSON; surface detailed errors to the user

Data conventions
- Schema-first:
  - Update validation/schemas and docs/DATA-SCHEMAS.md when changing formats
- IDs:
  - Use lowercase, hyphen/underscore-separated ids where applicable (e.g., basic_strike)
- Localization:
  - Keep Chinese display names in data; ids should remain stable even if names change

Documentation conventions
- Place developer docs under docs/
- Keep README.md at the root or docs/README.md as an entry point
- Use Mermaid where helpful, but avoid double quotes inside [] in Mermaid diagrams
- Include rationale for architectural decisions in ARCHITECTURE.md

PR hygiene
- Small diffs with tests and docs updated
- Provide deterministic seeds and steps to reproduce for any behavioral changes
- Avoid drive-by API changes that break the GUI or data loaders

Examples
- Engine method signatures:
  - BattleEngine(state, ai, clock, rng, processor_registry)
  - TextNarrator(index, rng, template_engine)
- Good:
  def select_action(self, actor, state) -> Optional[Tuple[str, str, int]]
- Avoid:
  def select_action(self, *args, **kwargs)