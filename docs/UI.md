# UI: Tkinter MVP, Progressive Narrator, Editors

The UI provides an end-to-end way to run deterministic battles, visualize outcomes, and edit data files directly with validation.

Launch
- python -m wuxia_battle_simulator.ui.run_ui

Tabs and layout
- Battle Simulator
  - Controls:
    - RNG Seed: integer seed for deterministic runs
    - Narrator: Finish or Progressive
      - Finish prints all narration at once
      - Progressive schedules each narration line with a delay
    - Step (s): delay per event in Progressive mode (float, default 0.5)
    - Run, Replay Seed, Clear Log
  - Team A and Team B selectors:
    - Two listboxes support multi-select; selections are independent and visually highlighted
  - Commentary:
    - Text area showing narrated lines
    - Two live status strings above commentary displaying Team A and Team B HP snapshots (name current/max). Updated at start, after each event, and at end

Editors menu
- Characters…
  - CharacterEditorView: list of characters with editable form for:
    - id, name, faction
    - stats: hp, qi, agility
    - skills: “skill_id:tier” comma-separated list
  - Operations: New, Save, Delete, Save to JSON (validates with schemas before writing)
  - On save: writes to characters.json in the opened data folder, then reloads data and refreshes views

- Skills…
  - SkillEditorView: list of skills and a form for:
    - id, name, type
    - tiers: editable text area (one tier per line: key=value;key=value)
  - Operations: New Skill, Add Tier, Remove Tier, Save, Save to JSON (validates and rebuilds runtime SkillDB)
  - On save: writes to skills.json, reloads data_dir() and SkillDB

Narration modes
- Finish Mode:
  - Simulator runs to completion; all events are rendered immediately
  - Live HP status lines update after rendering events
- Progressive Mode:
  - Simulator computes the full event list deterministically
  - The UI schedules one line at a time using Tk after() with the configured delay
  - HP status updates after each scheduled event
  - At the end, a summary line (winner / all down / stalemate) is printed and HP status is updated

Damage visibility
- The UI appends a suffix “（伤害: X）” to each narration line when the context contains a usable damage value (damage_amount, hp_delta, or damage).

Data folder workflow
- File -> Open Data Folder… selects a directory containing characters.json, skills.json, templates.json, config.json
- File -> Validate Data runs schema validation against current in-memory datasets
- Editors persist directly to those JSON files after validation

Error handling
- Invalid seed or missing selections produce message boxes
- Template issues, engine exceptions, or no-event scenarios are printed in commentary with “[调试] …” prefix
- Editors surface validation failures with detailed error messages; files are not written if validation fails

Extending the UI
- Replace listboxes with richer widgets (e.g., dual-list with add/remove controls)
- Add graphical HP bars next to names in status lines or as a mini HUD per team
- Add export buttons for battle logs, seed replay scripts, or JSON snapshots
- Add filters and search in the editors; replace tiers text area with grid-based form