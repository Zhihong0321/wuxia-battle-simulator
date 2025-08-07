# UI: Tkinter MVP, Progressive Narrator, Editors

The UI provides an end-to-end way to run deterministic battles, visualize outcomes, and edit data files directly with validation.

Launch
- python -m wuxia_battle_simulator.ui.run_ui

Tabs and layout
- Battle Engine
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
    - stats: hp, max_hp, qi, max_qi, strength, agility, defense
    - skills: grid with rows [skill_id, tier] instead of a comma list
  - Operations: New, Save, Delete, Save to JSON (validates with schemas before writing)
  - On save: writes to characters.json in the opened data folder, then reloads data and refreshes views

- Skills…
  - SkillEditorView: list of skills and a form for:
    - id, name, type
    - tiers: Treeview grid (inline editable) instead of free-form text
  - Operations: New Skill, Add Tier, Remove Tier, Save, Save to JSON (validates and rebuilds runtime SkillDB)
  - On save: persists to skills.json, reloads DataManager and SkillDB immediately

Narration modes
- Finish Mode:
  - Battle engine runs to completion; all events are rendered immediately
  - Live HP status lines update after rendering events
- Progressive Mode:
  - Battle engine computes the full event list deterministically
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
## Editors (Expanded Specification)

This section formalizes the Characters and Skills editors to support list, add new, edit selected flows with dedicated editor dialogs. All persistence actions validate against schemas before writing to disk, and the in-memory DataManager reloads upon successful save.

### Characters Editor

- Entry point
  - Menu: Editors -> Characters…
  - Implementation references:
    - List view and dialog classes to be added in [wuxia_battle_simulator.ui.run_ui.CharactersEditorView()](wuxia_battle_simulator/ui/run_ui.py:1) and [wuxia_battle_simulator.ui.run_ui.CharacterEditorDialog()](wuxia_battle_simulator/ui/run_ui.py:1)
    - Validation via [wuxia_battle_simulator.validation.validator.Validator](wuxia_battle_simulator/validation/validator.py:1)
    - Data access via [wuxia_battle_simulator.utils.data_loader.DataManager](wuxia_battle_simulator/utils/data_loader.py:1)

- List View (CharactersEditorView)
  - Layout
    - Left pane: Listbox of character ids with a filter entry above it.
    - Right pane: Details preview (read-only), showing name, faction, stats, equipped skills.
    - Footer actions: Add New, Edit Selected, Delete Selected, Save to JSON, Reload.
  - Behavior
    - Selecting a row shows preview in the right pane.
    - Filter narrows the list by id or name substring.
    - Add New opens CharacterEditorDialog initialized with sensible defaults for all stats.
    - Edit Selected opens CharacterEditorDialog for the highlighted character.
    - Delete Selected removes the character from in-memory model after a confirm dialog; requires Save to JSON to persist.
    - Save to JSON:
      - Assembles { "characters": [...] } payload from in-memory state.
      - Validates against [wuxia_battle_simulator.validation.schemas.characters.schema.json](wuxia_battle_simulator/validation/schemas/characters.schema.json:1).
      - If valid, writes to characters.json in the current data folder and reloads DataManager. If invalid, shows a modal with errors; file is not written.
    - Reload refreshes in-memory data and UI from disk via DataManager.

- Editor Dialog (CharacterEditorDialog)
  - Fields
    - id: string (must be unique across characters)
    - name: string
    - faction: string (optional)
    - stats: hp (int >= 1), max_hp (int >= hp), qi (int >= 0), max_qi (int >= qi), strength (int >= 0), agility (int >= 0), defense (int >= 0)
    - skills: tabular editor with rows of skill_id (string), tier (int >= 1); Add Row / Remove Row
  - Actions
    - Validate: Runs Validator against a temporary payload for the edited character merged into the current dataset.
    - Save:
      - Updates the in-memory dataset and closes the dialog.
      - Actual file write occurs from the parent list view on Save to JSON.
    - Cancel: Discards changes and closes the dialog.
  - Error handling
    - Validation failures display a scrollable error panel. No disk writes on failure.

- Determinism
  - UI-only; no effect on engine RNG paths. Seeded behavior preserved.

### Skills Editor

- Entry point
  - Menu: Editors -> Skills…
  - Implementation references:
    - List view and dialog classes in [wuxia_battle_simulator.ui.run_ui.SkillsEditorView()](wuxia_battle_simulator/ui/run_ui.py:1) and [wuxia_battle_simulator.ui.run_ui.SkillEditorDialog()](wuxia_battle_simulator/ui/run_ui.py:1)
    - Validation: [wuxia_battle_simulator.validation.validator.Validator](wuxia_battle_simulator/validation/validator.py:1)
    - SkillDB reload via [wuxia_battle_simulator.utils.data_loader.DataManager](wuxia_battle_simulator/utils/data_loader.py:1)

- List View (SkillsEditorView)
  - Layout
    - Left pane: Listbox of skill ids with filter entry.
    - Right pane: Read-only preview: id, name, type, tier count with a small table of key fields.
    - Footer actions: Add New, Edit Selected, Delete Selected, Save to JSON, Reload.
  - Behavior
    - Add New opens SkillEditorDialog with a new skill skeleton including an empty tiers list.
    - Edit Selected opens SkillEditorDialog for the chosen skill.
    - Delete Selected removes the skill from in-memory model after confirmation; requires Save to JSON to persist.
    - Save to JSON:
      - Assembles { "skills": [...] } payload.
      - Validates against [wuxia_battle_simulator.validation.schemas.skills.schema.json](wuxia_battle_simulator/validation/schemas/skills.schema.json:1).
      - If valid, writes to skills.json, then triggers DataManager reload and SkillDB rebuild; otherwise shows errors.
    - Reload refreshes in-memory data and UI from disk via DataManager.

- Editor Dialog (SkillEditorDialog)
  - Fields
    - id: string (unique), name: string, type: string (e.g., 攻击)
    - tiers: Treeview grid with columns:
      - tier (int >= 1)
      - base_damage (integer >= 0)
      - hit_chance (number in [0, 1])
      - crit_chance (number in [0, 1])
      - qi_cost (int >= 0)
      - cooldown (int >= 0)
      - power_multiplier (number >= 0)
      - tier_name (string)
      - narrative_template (string; opens a modal multiline editor)
    - Row controls: Add Tier, Remove Tier; rows auto-sort by tier when saved.
  - Inline editing behavior
    - Double/single-click to edit cells; Entry overlay commits on FocusOut.
    - narrative_template opens a modal dialog for multi-line text; validated as non-empty.
    - Active edits are committed before Save to prevent value loss.
  - Validation and serialization
    - Each row is validated with constraints above.
    - On Save, tiers are serialized with a nested parameters object:
      - parameters: { base_damage, power_multiplier, hit_chance, critical_chance, qi_cost, cooldown }
    - narrative_template and tier_name are saved per tier.
    - Immediate persistence: Save writes to skills.json and triggers a reload of DataManager and SkillDB.
  - Actions
    - Validate: Runs Validator on a temporary skills payload.
    - Save: Updates in-memory dataset and persists immediately to disk (with validation).
    - Cancel: Closes without applying changes.

- Determinism
  - Editing data does not change engine algorithms; run-time determinism remains intact as long as data and seed are fixed.

### Validation and Persistence Rules

- Schema-first
  - All writes are blocked unless the dataset validates against the corresponding JSON Schema:
    - Characters: [wuxia_battle_simulator.validation.schemas.characters.schema.json](wuxia_battle_simulator/validation/schemas/characters.schema.json:1)
    - Skills: [wuxia_battle_simulator.validation.schemas.skills.schema.json](wuxia_battle_simulator/validation/schemas/skills.schema.json:1)
- DataManager integration
  - On successful Save to JSON:
    - Characters: reload characters; update dependent UI.
    - Skills: reload skills; rebuild SkillDB; update dependent UI.
- Error surfaces
  - Validation errors displayed in a modal with a scrollable text area and a [调试] prefix for commentary consistency.

### Minimal Flow Diagrams

- Characters Editor flow:
  - Open Characters… -> List view -> [Add New | Edit Selected | Delete Selected] -> Validate -> Save (in-memory) -> Save to JSON -> Validate datasets -> Write -> Reload DataManager -> Refresh UI

- Skills Editor flow:
  - Open Skills… -> List view -> [Add New | Edit Selected | Delete Selected] -> Validate -> Save (in-memory) -> Save to JSON -> Validate datasets -> Write -> Reload DataManager + SkillDB -> Refresh UI

### Testing Recommendations

- Schema round-trip (data)
  - After Add New and Edit workflows, assemble payloads and validate pass cases.
  - Negative cases (e.g., hit_chance 1.2, agility -1) must fail and block persistence.
- UI smoke (optional)
  - Instantiate views without Tk mainloop; verify proper calls to Validator and DataManager on Save to JSON.
- Add filters and search in the editors; tiers are edited via a grid with validators and per-tier narrative templates