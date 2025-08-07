# 千文传 (Thousand Texts Saga) — Wuxia Battle Simulator (MVP)

Project root: `wuxia_battle_simulator`  
Target Python: 3.9

Scope: ATB-based battle simulator that emits structured events and renders Wuxia-style narration via templates. Simple Tkinter UI displays narrative feed and character stats. Internal event types are English (attack, defend, dodge, critical) and mapped to Chinese for narration/templates.

Structure
- `main.py` — Entry point, wires DataManager, ATB engine, Narrator, and UI.
- `engine/` — ATB clock, simulator, game state, AI policy, event mappers.
- `narrator/` — Template index, variable resolution, narration rendering.
- `utils/` — Data loading, template engine, logging.
- `validation/` — JSON Schemas and validator.
- `ui/` — Tkinter app and components.
- `data/` — Static JSON content (characters, skills, templates, config).

Run (placeholder)
- Ensure Python 3.9 and `pip install -r requirements.txt` once created.
- Start MVP: `python -m wuxia_battle_simulator.main`