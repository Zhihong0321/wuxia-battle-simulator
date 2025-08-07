import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import sys
from typing import List, Dict, Any, Optional, Tuple

# Robust path setup to support both:
# - python -m wuxia_battle_simulator.ui.run_ui (package mode)
# - python wuxia_battle_simulator/ui/run_ui.py (script mode)
_THIS_DIR = os.path.dirname(__file__)
_PKG_DIR = os.path.abspath(os.path.join(_THIS_DIR, ".."))           # e:/qianwen-legend/wuxia_battle_simulator
_PROJECT_DIR = os.path.abspath(os.path.join(_THIS_DIR, "..", "..")) # e:/qianwen-legend
# Ensure project dir is first on sys.path so 'wuxia_battle_simulator' resolves as a package
if _PROJECT_DIR in sys.path:
    sys.path.remove(_PROJECT_DIR)
sys.path.insert(0, _PROJECT_DIR)
# Also ensure package dir is importable as a fallback
if _PKG_DIR not in sys.path:
    sys.path.insert(1, _PKG_DIR)

# Try package imports first, fallback to creating __init__.py on the fly to help local runs
try:
    from wuxia_battle_simulator.utils.data_loader import DataManager
    from wuxia_battle_simulator.validation.validator import Validator, ValidationError
    from wuxia_battle_simulator.engine.battle_simulator import BattleSimulator
    from wuxia_battle_simulator.narrator.text_narrator import TextNarrator
except ModuleNotFoundError:
    # Attempt to create missing __init__.py files for local repo layout
    for pkg in ("engine", "narrator", "validation", "utils"):
        init_path = os.path.join(_PKG_DIR, pkg, "__init__.py")
        pkg_dir = os.path.dirname(init_path)
        if os.path.isdir(pkg_dir) and not os.path.exists(init_path):
            try:
                with open(init_path, "w", encoding="utf-8") as f:
                    f.write("# package\n")
            except Exception:
                pass
    # Try imports again (use data_loader.DataManager which matches repository)
    from wuxia_battle_simulator.utils.data_loader import DataManager
    from wuxia_battle_simulator.validation.validator import Validator, ValidationError
    from wuxia_battle_simulator.engine.battle_simulator import BattleSimulator
    from wuxia_battle_simulator.narrator.text_narrator import TextNarrator


class BattleSimulatorView(ttk.Frame):
    def __init__(self, master, app_context):
        super().__init__(master)
        self.app = app_context
        self._build()
        
    def _sync_selection_styles(self):
        # Ensure selection stays visible after focus switches (exportselection=False already does most of it)
        # This method exists for future per-item highlighting if needed.
        self.team_a_list.update_idletasks()
        self.team_b_list.update_idletasks()
        
    def _sync_selection_styles(self):
        # No-op placeholder to force visual refresh; Listbox handles colors automatically with configured selectbackground/foreground.
        # But we can ensure that selections remain visible even when focus moves by toggling exportselection off (already set).
        # This method exists to be extended if future per-item styling is desired.
        self.team_a_list.update_idletasks()
        self.team_b_list.update_idletasks()

    def _build(self):
        # Top controls
        controls = ttk.Frame(self)
        controls.pack(fill="x", padx=8, pady=8)

        ttk.Label(controls, text="RNG Seed:").grid(row=0, column=0, sticky="w")
        self.seed_var = tk.StringVar(value=str(self.app.config_data.get("rng_seed", 42)))
        seed_entry = ttk.Entry(controls, textvariable=self.seed_var, width=12)
        seed_entry.grid(row=0, column=1, sticky="w", padx=4)

        # Narration mode: Finish (all at once) or Progressive (timed)
        ttk.Label(controls, text="Narrator:").grid(row=0, column=2, sticky="w")
        self.mode_var = tk.StringVar(value="Finish")
        mode_combo = ttk.Combobox(controls, textvariable=self.mode_var, values=("Finish","Progressive"), width=12, state="readonly")
        mode_combo.grid(row=0, column=3, sticky="w", padx=(4, 12))
        mode_combo.set("Finish")

        ttk.Label(controls, text="Step (s):").grid(row=0, column=4, sticky="w")
        self.step_seconds_var = tk.StringVar(value="0.5")
        step_entry = ttk.Entry(controls, textvariable=self.step_seconds_var, width=6)
        step_entry.grid(row=0, column=5, sticky="w", padx=(4, 12))

        run_btn = ttk.Button(controls, text="Run", command=self.on_run)
        run_btn.grid(row=0, column=6, padx=8)

        replay_btn = ttk.Button(controls, text="Replay Seed", command=self.on_replay)
        replay_btn.grid(row=0, column=7, padx=4)

        clear_btn = ttk.Button(controls, text="Clear Log", command=self.on_clear)
        clear_btn.grid(row=0, column=8, padx=4)

        # Team selectors
        teams = ttk.Frame(self)
        teams.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        
        left_frame = ttk.LabelFrame(teams, text="Team A")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 4))
        right_frame = ttk.LabelFrame(teams, text="Team B")
        right_frame.pack(side="left", fill="both", expand=True, padx=(4, 0))
        
        # Use extended selection in both lists and make selection visually obvious
        self.team_a_list = tk.Listbox(left_frame, selectmode="extended", exportselection=False)
        self.team_a_list.pack(fill="both", expand=True, padx=6, pady=6)
        self.team_a_list.configure(selectbackground="#2d7cff", selectforeground="white", activestyle="dotbox")
        
        self.team_b_list = tk.Listbox(right_frame, selectmode="extended", exportselection=False)
        self.team_b_list.pack(fill="both", expand=True, padx=6, pady=6)
        self.team_b_list.configure(selectbackground="#2d7cff", selectforeground="white", activestyle="dotbox")
        
        # Keep selections independent across listboxes (exportselection=False already helps on Windows/Linux)
        # Additionally, re-apply selection highlight on focus changes
        self.team_a_list.bind("<<ListboxSelect>>", lambda e: self._sync_selection_styles())
        self.team_b_list.bind("<<ListboxSelect>>", lambda e: self._sync_selection_styles())
        self.team_a_list.bind("<FocusIn>", lambda e: self._sync_selection_styles())
        self.team_b_list.bind("<FocusIn>", lambda e: self._sync_selection_styles())

        # Commentary output + live HP status bars
        out_frame = ttk.LabelFrame(self, text="Commentary")
        out_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Live team status
        status_wrap = ttk.Frame(out_frame)
        status_wrap.pack(fill="x", padx=6, pady=(6, 0))
        self.team_a_status = tk.StringVar(value="Team A: -")
        self.team_b_status = tk.StringVar(value="Team B: -")
        ttk.Label(status_wrap, textvariable=self.team_a_status, anchor="w").pack(side="left", fill="x", expand=True)
        ttk.Label(status_wrap, textvariable=self.team_b_status, anchor="e").pack(side="left", fill="x", expand=True)

        self.text = tk.Text(out_frame, height=18, wrap="word")
        self.text.pack(fill="both", expand=True, padx=6, pady=6)
        self.text.configure(state="disabled")

        self._populate_lists()
        # Bind events to keep visual selection obvious even when focus changes
        for lb in (self.team_a_list, self.team_b_list):
            lb.bind("<<ListboxSelect>>", lambda e: self._sync_selection_styles())
            lb.bind("<FocusIn>", lambda e: self._sync_selection_styles())
            lb.bind("<FocusOut>", lambda e: self._sync_selection_styles())

    def _populate_lists(self):
        self.team_a_list.delete(0, tk.END)
        self.team_b_list.delete(0, tk.END)
        for ch in self.app.characters:
            label = f"{ch.get('name', ch.get('id'))} [{ch.get('faction', '')}]"
            self.team_a_list.insert(tk.END, label)
            self.team_b_list.insert(tk.END, label)

    def _selected_indices(self, listbox: tk.Listbox) -> List[int]:
        try:
            return list(map(int, listbox.curselection()))
        except Exception:
            return []

    def _gather_teams(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        a_idx = self._selected_indices(self.team_a_list)
        b_idx = self._selected_indices(self.team_b_list)
        team_a = [self.app.characters[i] for i in a_idx] if a_idx else []
        team_b = [self.app.characters[i] for i in b_idx] if b_idx else []
        return team_a, team_b

    def _append_log(self, line: str):
        self.text.configure(state="normal")
        self.text.insert(tk.END, line + "\n")
        self.text.see(tk.END)
        self.text.configure(state="disabled")

    def on_clear(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", tk.END)
        self.text.configure(state="disabled")
        # Reset status bars
        self.team_a_status.set("Team A: -")
        self.team_b_status.set("Team B: -")

    def on_replay(self):
        # Replay with current seed var
        self.on_run(replay=True)

    def on_run(self, replay: bool = False):
        try:
            seed = int(self.seed_var.get())
        except ValueError:
            messagebox.showerror("Invalid Seed", "Seed must be an integer.")
            return
        # parse progressive step seconds
        try:
            step_seconds = float(self.step_seconds_var.get())
            if step_seconds < 0: step_seconds = 0.0
        except Exception:
            step_seconds = 0.5
        progressive = (self.mode_var.get().lower() == "progressive")

        team_a, team_b = self._gather_teams()
        if not team_a or not team_b:
            messagebox.showwarning("Select Teams", "Please select at least one character for each team.")
            return
        
        # Prepare simulator and narrator hook
        # Build engine components expected by BattleSimulator(state, ai, clock, rng)
        from wuxia_battle_simulator.engine.ai_policy import HeuristicAI
        from wuxia_battle_simulator.engine.atb_system import ATBClock
        import random
        # Build runtime state from selected characters using DataManager
        # Ensure selected characters have at least 1 skill each; otherwise add a zero-cost placeholder to allow progress
        selected_defs = []
        for c in (team_a + team_b):
            c2 = dict(c)
            c2.setdefault("skills", c2.get("skills", []))
            if not c2["skills"]:
                # Fallback: inject a default skill reference present in sample data, or a safe placeholder id
                c2["skills"] = [{"skill_id": c2.get("default_skill_id", "basic_strike"), "tier": 1}]
            selected_defs.append(c2)
        state = self.app.data_manager.build_game_state(selected_defs)
        # Skills DB already produced by DataManager.load_skills
        skills_db = self.app.skills
        rng = random.Random(seed)
        ai = HeuristicAI(rng=rng, skills_db=skills_db)
        clock = ATBClock(threshold=self.app.config_data.get("atb_threshold", 100),
                         tick_scale=self.app.config_data.get("atb_tick_scale", 1.0))
        simulator = BattleSimulator(state, ai, clock, rng)

        # helper: update live HP status bars from simulator state
        def _update_hp_status_from_state():
            try:
                # Simulator state exposes living/actors; map back to initial team splits by name/id
                # Build sets of names for quick membership
                team_a_names = set(ch.get("name", ch.get("id")) for ch in team_a)
                team_b_names = set(ch.get("name", ch.get("id")) for ch in team_b)
                a_parts, b_parts = [], []
                # Expect state.actors iterable of CharacterState with .name, .hp, .max_hp
                for actor in simulator.state.actors():
                    part = f"{getattr(actor,'name','?')} {getattr(actor,'hp','?')}/{getattr(actor,'max_hp', getattr(getattr(actor,'stats',None),'hp','?'))}"
                    if getattr(actor, 'name', None) in team_a_names:
                        a_parts.append(part)
                    elif getattr(actor, 'name', None) in team_b_names:
                        b_parts.append(part)
                self.team_a_status.set("Team A: " + (" | ".join(a_parts) if a_parts else "-"))
                self.team_b_status.set("Team B: " + (" | ".join(b_parts) if b_parts else "-"))
            except Exception:
                # Fallback to no-op if structure differs
                pass

        # TextNarrator requires rng and a template engine with a variable resolver
        from wuxia_battle_simulator.utils.template_engine import TemplateEngine
        from wuxia_battle_simulator.narrator.variable_resolver import VariableResolver
        tmpl_engine = TemplateEngine(resolver=VariableResolver())
        # Wrap templates list with a simple index providing select()
        class _SimpleTemplateIndex:
            def __init__(self, templates_list):
                self._templates = templates_list or []
            def select(self, narrative_type: str, context: dict):
                # filter by narrative_type first
                candidates = [t for t in self._templates if t.get("narrative_type") == narrative_type]
                # basic conditions support: all key==value pairs in conditions must match context
                def _match_conditions(tpl, ctx):
                    cond = tpl.get("conditions") or {}
                    try:
                        for k, v in cond.items():
                            if ctx.get(k) != v:
                                return False
                        return True
                    except Exception:
                        return True
                return [t for t in candidates if _match_conditions(t, context)]
        templates_index = _SimpleTemplateIndex(self.app.templates)
        narrator = TextNarrator(templates_index, rng=rng, template_engine=tmpl_engine)
        # Initial HP snapshot
        _update_hp_status_from_state()
        
        # Run battle, either finish mode or progressive mode
        self._append_log("——— 战斗开始 ———")
        produced = 0
        # Prefer TextNarrator.render(); fall back if older API exists
        use_render = hasattr(narrator, "render")
        use_narrate = hasattr(narrator, "narrate")

        try:
            events = simulator.run_to_completion()
        except Exception as e:
            self._append_log(f"[调试] 模拟器异常: {e!r}")
            events = []

        if not events:
            self._append_log("[调试] 没有产生事件（可能因两方无法行动、冷却或气不足）")

        def _render_line(ctx: dict) -> str:
            if use_render:
                line = narrator.render(ctx)
            elif use_narrate:
                line = narrator.narrate(ctx)
            else:
                raise AttributeError("TextNarrator has neither render() nor narrate()")
            dmg = ctx.get("damage_amount") or ctx.get("hp_delta") or ctx.get("damage")
            if isinstance(dmg, (int, float)):
                line = f"{line}（伤害: {int(dmg)}）"
            return line

        if not progressive:
            # Finish Mode: print all at once
            for ev in events:
                try:
                    ctx = simulator.map_event_for_narration(ev)
                    line = _render_line(ctx)
                except Exception as e:
                    line = f"[调试] 事件叙事失败: {e!r}"
                self._append_log(line)
                produced += 1
                try:
                    _update_hp_status_from_state()
                except Exception:
                    pass
            # outcome summary
            living = [c for c in simulator.state.living()]
            if len(living) == 1:
                self._append_log(f"结果: {living[0].name} 存活")
            elif len(living) == 0 and produced > 0:
                self._append_log("结果: 全员倒下")
            elif produced == 0:
                self._append_log("结果: 本回合无有效动作（可能因冷却或资源不足）")
            else:
                self._append_log("结果: 战斗未决")
            try:
                _update_hp_status_from_state()
            except Exception:
                pass
            self._append_log("——— 战斗结束 ———")
        else:
            # Progressive Mode: use Tk after() to step through events
            self._progress_idx = 0
            self._progress_events = events
            self._progress_produced = 0
            delay_ms = int(step_seconds * 1000) if step_seconds > 0 else 500

            def _step():
                if self._progress_idx >= len(self._progress_events):
                    # finish and summary
                    living = [c for c in simulator.state.living()]
                    if len(living) == 1:
                        self._append_log(f"结果: {living[0].name} 存活")
                    elif len(living) == 0 and self._progress_produced > 0:
                        self._append_log("结果: 全员倒下")
                    elif self._progress_produced == 0:
                        self._append_log("结果: 本回合无有效动作（可能因冷却或资源不足）")
                    else:
                        self._append_log("结果: 战斗未决")
                    try:
                        _update_hp_status_from_state()
                    except Exception:
                        pass
                    self._append_log("——— 战斗结束 ———")
                    return
                ev = self._progress_events[self._progress_idx]
                try:
                    ctx = simulator.map_event_for_narration(ev)
                    line = _render_line(ctx)
                except Exception as e:
                    line = f"[调试] 事件叙事失败: {e!r}"
                self._append_log(line)
                self._progress_produced += 1
                try:
                    _update_hp_status_from_state()
                except Exception:
                    pass
                self._progress_idx += 1
                # schedule next
                self.after(delay_ms, _step)

            # kick off progressive narrator
            self.after(delay_ms, _step)


class CharactersListView(ttk.Frame):
    def __init__(self, master, app_context):
        super().__init__(master)
        self.app = app_context
        self._build()

    def _build(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=8, pady=6)

        refresh_btn = ttk.Button(toolbar, text="Refresh", command=self.refresh)
        refresh_btn.pack(side="left")

        self.tree = ttk.Treeview(self, columns=("id", "name", "faction", "hp"), show="headings")
        self.tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Name")
        self.tree.heading("faction", text="Faction")
        self.tree.heading("hp", text="HP")
        self.refresh()

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for ch in self.app.characters:
            stats = ch.get("stats", {})
            hp = stats.get("hp", "")
            self.tree.insert("", "end", values=(ch.get("id", ""), ch.get("name", ""),
                                                ch.get("faction", ""), hp))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Wuxia Battle Simulator - MVP GUI")
        self.geometry("900x600")
        self.minsize(900, 600)

        self.data_dir: Optional[str] = None
        self.characters: List[Dict[str, Any]] = []
        self.skills: List[Dict[str, Any]] = []
        self.templates: List[Dict[str, Any]] = []
        # Avoid shadowing Tk.config() method; use config_data for app configuration
        self.config_data: Dict[str, Any] = {}
        
        # Initialize validator with schemas directory, then pass it to DataManager
        self.schemas_dir = os.path.join(_PKG_DIR, "schemas")
        self.validator = Validator(self.schemas_dir)
        self.data_manager = DataManager(self.validator)

        self._build_menu()
        self._build_layout()

        # Try to locate default data folder if exists
        default_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
        if os.path.isdir(default_dir):
            self.load_data_dir(default_dir)

    def _build_menu(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Open Data Folder...", command=self.choose_data_dir)
        file_menu.add_separator()
        file_menu.add_command(label="Validate Data", command=self.validate_all)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_menu)

        # Editors menu
        editors_menu = tk.Menu(menubar, tearoff=False)
        editors_menu.add_command(label="Characters...", command=self.open_character_editor)
        editors_menu.add_command(label="Skills...", command=self.open_skill_editor)
        menubar.add_cascade(label="Editors", menu=editors_menu)

        self.config_menu = menubar
        self.configure(menu=menubar)

    def _build_layout(self):
        # Tabs: Battle Simulator, Characters (read-only)
        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True)

        self.battle_view = BattleSimulatorView(tabs, self)
        tabs.add(self.battle_view, text="Battle Simulator")

        self.characters_view = CharactersListView(tabs, self)
        tabs.add(self.characters_view, text="Characters")
        # place-holders for editor tabs
        self._tabs = tabs
        self._char_editor = None
        self._skill_editor = None

        # Status bar
        self.status = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self, textvariable=self.status, anchor="w")
        status_bar.pack(fill="x", padx=6, pady=(0, 4))

    def choose_data_dir(self):
        path = filedialog.askdirectory(title="Select data folder (contains characters.json, skills.json, templates.json, config.json)")
        if path:
            self.load_data_dir(path)

    def load_data_dir(self, path: str):
        try:
            chars_p = os.path.join(path, "characters.json")
            skills_p = os.path.join(path, "skills.json")
            templates_p = os.path.join(path, "templates.json")
            config_p = os.path.join(path, "config.json")
            
            with open(chars_p, "r", encoding="utf-8") as f:
                characters = json.load(f)
            with open(skills_p, "r", encoding="utf-8") as f:
                skills = json.load(f)
            with open(templates_p, "r", encoding="utf-8") as f:
                templates = json.load(f)
            with open(config_p, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            
            # Validate with existing Validator which supports logical keys
            self.validator.validate("characters", characters)
            self.validator.validate("skills", skills)
            self.validator.validate("templates", templates)
            self.validator.validate("config", config_data)
            
            # Assign
            self.data_dir = path
            self.characters = characters["characters"] if isinstance(characters, dict) and "characters" in characters else characters
            # Build runtime SkillDB so AI/Simulator can query tiers/params
            from pathlib import Path as _P
            self.skills = self.data_manager.load_skills(_P(path) / "skills.json")
            self.templates = templates["templates"] if isinstance(templates, dict) and "templates" in templates else templates
            self.config_data = config_data
            
            # Refresh views
            self.battle_view._populate_lists()
            self.characters_view.refresh()
            
            self.status.set(f"Loaded data from: {path}")
        except ValidationError as ve:
            messagebox.showerror("Validation Error", str(ve))
            self.status.set("Validation failed")
        except FileNotFoundError as fe:
            messagebox.showerror("File Not Found", str(fe))
            self.status.set("File not found")
        except json.JSONDecodeError as je:
            messagebox.showerror("JSON Error", f"JSON parse error: {je}")
            self.status.set("JSON parse error")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {e}")
            self.status.set("Load error")

    def validate_all(self):
        if self.data_dir is None:
            messagebox.showinfo("No Data", "Please open a data folder first.")
            return
        try:
            self.validator.validate("characters", self.characters)
            self.validator.validate("skills", self.skills)
            self.validator.validate("templates", self.templates)
            self.validator.validate("config", self.config_data)
            messagebox.showinfo("Validation", "All datasets validated successfully.")
            self.status.set("Validation OK")
        except ValidationError as ve:
            messagebox.showerror("Validation Error", str(ve))
            self.status.set("Validation failed")

    # --- Editors: Character and Skill (MVP CRUD) ---
    def open_character_editor(self):
        if self._char_editor is None or not self._char_editor.winfo_exists():
            self._char_editor = CharacterEditorView(self._tabs, self)
            self._tabs.add(self._char_editor, text="Character Editor")
        self._tabs.select(self._char_editor)

    def open_skill_editor(self):
        if self._skill_editor is None or not self._skill_editor.winfo_exists():
            self._skill_editor = SkillEditorView(self._tabs, self)
            self._tabs.add(self._skill_editor, text="Skill Editor")
        self._tabs.select(self._skill_editor)


# --- Character Editor View ---
class CharacterEditorView(ttk.Frame):
    def __init__(self, master, app_context):
        super().__init__(master)
        self.app = app_context
        self._build()

    def _build(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=8, pady=6)
        ttk.Button(toolbar, text="New", command=self.new_character).pack(side="left")
        ttk.Button(toolbar, text="Save", command=self.save_current).pack(side="left")
        ttk.Button(toolbar, text="Delete", command=self.delete_current).pack(side="left")
        ttk.Button(toolbar, text="Save to JSON", command=self.save_to_json).pack(side="left")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=8, pady=6)

        self.listbox = tk.Listbox(body, exportselection=False)
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", lambda e: self._load_selected())

        form = ttk.Frame(body)
        form.pack(side="left", fill="both", expand=True, padx=(8,0))

        # Basic fields
        ttk.Label(form, text="ID").grid(row=0, column=0, sticky="e"); self.id_var = tk.StringVar(); ttk.Entry(form, textvariable=self.id_var, width=40).grid(row=0, column=1, sticky="w")
        ttk.Label(form, text="Name").grid(row=1, column=0, sticky="e"); self.name_var = tk.StringVar(); ttk.Entry(form, textvariable=self.name_var, width=40).grid(row=1, column=1, sticky="w")
        ttk.Label(form, text="Faction").grid(row=2, column=0, sticky="e"); self.faction_var = tk.StringVar(); ttk.Entry(form, textvariable=self.faction_var, width=40).grid(row=2, column=1, sticky="w")
        ttk.Label(form, text="HP").grid(row=3, column=0, sticky="e"); self.hp_var = tk.IntVar(); ttk.Spinbox(form, from_=1, to=9999, textvariable=self.hp_var, width=8).grid(row=3, column=1, sticky="w")
        ttk.Label(form, text="QI").grid(row=4, column=0, sticky="e"); self.qi_var = tk.IntVar(); ttk.Spinbox(form, from_=0, to=9999, textvariable=self.qi_var, width=8).grid(row=4, column=1, sticky="w")
        ttk.Label(form, text="Agility").grid(row=5, column=0, sticky="e"); self.agi_var = tk.IntVar(); ttk.Spinbox(form, from_=0, to=9999, textvariable=self.agi_var, width=8).grid(row=5, column=1, sticky="w")
        ttk.Label(form, text="Skills (skill_id:tier, comma-separated)").grid(row=6, column=0, sticky="e"); self.skills_var = tk.StringVar(); ttk.Entry(form, textvariable=self.skills_var, width=40).grid(row=6, column=1, sticky="w")

        self.refresh_list()

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for ch in self.app.characters:
            self.listbox.insert(tk.END, f"{ch.get('name', ch.get('id'))}")

    def _load_selected(self):
        sel = self.listbox.curselection()
        if not sel: return
        ch = self.app.characters[sel[0]]
        stats = ch.get("stats", {})
        self.id_var.set(ch.get("id",""))
        self.name_var.set(ch.get("name",""))
        self.faction_var.set(ch.get("faction",""))
        self.hp_var.set(int(stats.get("hp", 100)))
        self.qi_var.set(int(stats.get("qi", 100)))
        self.agi_var.set(int(stats.get("agility", 10)))
        # serialize equipped skills
        skills = ch.get("skills", [])
        self.skills_var.set(",".join(f"{s.get('skill_id')}:{int(s.get('tier',1))}" for s in skills if s.get("skill_id")))

    def _collect_form(self):
        skills_txt = self.skills_var.get().strip()
        skills = []
        if skills_txt:
            for item in skills_txt.split(","):
                try:
                    sid, tier = item.split(":")
                    skills.append({"skill_id": sid.strip(), "tier": int(tier)})
                except Exception:
                    pass
        return {
            "id": self.id_var.get().strip(),
            "name": self.name_var.get().strip(),
            "faction": self.faction_var.get().strip(),
            "stats": {"hp": int(self.hp_var.get()), "qi": int(self.qi_var.get()), "agility": int(self.agi_var.get())},
            "skills": skills
        }

    def new_character(self):
        new = {"id":"new_char","name":"新角色","faction":"","stats":{"hp":100,"qi":100,"agility":10},"skills":[]}
        self.app.characters.append(new)
        self.refresh_list()
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(tk.END)

    def save_current(self):
        sel = self.listbox.curselection()
        if not sel: return
        self.app.characters[sel[0]] = self._collect_form()
        self.refresh_list()

    def delete_current(self):
        sel = self.listbox.curselection()
        if not sel: return
        del self.app.characters[sel[0]]
        self.refresh_list()

    def save_to_json(self):
        # persist to characters.json with validation
        try:
            payload = {"characters": self.app.characters} if isinstance(self.app.characters, list) else self.app.characters
            self.app.validator.validate("characters", payload)
            path = os.path.join(self.app.data_dir, "characters.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            self.app.load_data_dir(self.app.data_dir)
            messagebox.showinfo("Saved", "Characters saved.")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

# --- Skill Editor View ---
class SkillEditorView(ttk.Frame):
    def __init__(self, master, app_context):
        super().__init__(master)
        self.app = app_context
        self._build()

    def _build(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=8, pady=6)
        ttk.Button(toolbar, text="New Skill", command=self.new_skill).pack(side="left")
        ttk.Button(toolbar, text="Add Tier", command=self.add_tier).pack(side="left")
        ttk.Button(toolbar, text="Remove Tier", command=self.remove_tier).pack(side="left")
        ttk.Button(toolbar, text="Save", command=self.save_current).pack(side="left")
        ttk.Button(toolbar, text="Save to JSON", command=self.save_to_json).pack(side="left")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=8, pady=6)

        self.listbox = tk.Listbox(body, exportselection=False)
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", lambda e: self._load_selected())

        form = ttk.Frame(body)
        form.pack(side="left", fill="both", expand=True, padx=(8,0))

        ttk.Label(form, text="ID").grid(row=0, column=0, sticky="e"); self.id_var = tk.StringVar(); ttk.Entry(form, textvariable=self.id_var, width=40).grid(row=0, column=1, sticky="w")
        ttk.Label(form, text="Name").grid(row=1, column=0, sticky="e"); self.name_var = tk.StringVar(); ttk.Entry(form, textvariable=self.name_var, width=40).grid(row=1, column=1, sticky="w")
        ttk.Label(form, text="Type").grid(row=2, column=0, sticky="e"); self.type_var = tk.StringVar(); ttk.Entry(form, textvariable=self.type_var, width=40).grid(row=2, column=1, sticky="w")

        # Tiers as a simple text area: one tier per line with key=value;key=value
        ttk.Label(form, text="Tiers (one per line, key=value;...)").grid(row=3, column=0, sticky="ne")
        self.tiers_text = tk.Text(form, height=10, width=60)
        self.tiers_text.grid(row=3, column=1, sticky="w")

        self.refresh_list()

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        # self.app.skills is runtime SkillDB; fetch raw editable form by loading file directly
        try:
            skills_path = os.path.join(self.app.data_dir, "skills.json")
            with open(skills_path, "r", encoding="utf-8") as f:
                dat = json.load(f)
            self._skills_raw = dat["skills"] if isinstance(dat, dict) and "skills" in dat else dat
        except Exception:
            self._skills_raw = []
        for s in self._skills_raw:
            self.listbox.insert(tk.END, f"{s.get('name', s.get('id'))}")

    def _load_selected(self):
        sel = self.listbox.curselection()
        if not sel: return
        s = self._skills_raw[sel[0]]
        self.id_var.set(s.get("id",""))
        self.name_var.set(s.get("name",""))
        self.type_var.set(s.get("type",""))
        # tiers to text
        self.tiers_text.delete("1.0", tk.END)
        tiers = s.get("tiers", [])
        for t in tiers:
            line = ";".join(f"{k}={v}" for k,v in t.items())
            self.tiers_text.insert(tk.END, line + "\n")

    def _collect_form(self):
        tiers_lines = self.tiers_text.get("1.0", tk.END).strip().splitlines()
        tiers = []
        for line in tiers_lines:
            if not line.strip(): continue
            kv = {}
            for pair in line.split(";"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    k = k.strip()
                    v = v.strip()
                    # basic number casting
                    if v.isdigit():
                        v = int(v)
                    else:
                        try:
                            v = float(v)
                        except Exception:
                            pass
                    kv[k] = v
            tiers.append(kv)
        return {
            "id": self.id_var.get().strip(),
            "name": self.name_var.get().strip(),
            "type": self.type_var.get().strip(),
            "tiers": tiers
        }

    def new_skill(self):
        self._skills_raw.append({"id":"new_skill","name":"新武学","type":"攻击","tiers":[{"tier":1,"base_damage":10,"qi_cost":0,"cooldown":0,"hit_chance":1.0,"crit_chance":0.1}]})
        self.refresh_list()
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(tk.END)

    def add_tier(self):
        sel = self.listbox.curselection()
        if not sel: return
        s = self._skills_raw[sel[0]]
        tiers = s.setdefault("tiers", [])
        next_tier = 1 + max((int(t.get("tier", 0)) for t in tiers), default=0)
        tiers.append({"tier": next_tier, "base_damage": 10, "qi_cost": 0, "cooldown": 0, "hit_chance": 1.0, "crit_chance": 0.1})
        self._load_selected()

    def remove_tier(self):
        sel = self.listbox.curselection()
        if not sel: return
        s = self._skills_raw[sel[0]]
        tiers = s.setdefault("tiers", [])
        if tiers:
            tiers.pop()
        self._load_selected()

    def save_current(self):
        sel = self.listbox.curselection()
        if not sel: return
        self._skills_raw[sel[0]] = self._collect_form()
        self.refresh_list()

    def save_to_json(self):
        try:
            payload = {"skills": self._skills_raw}
            self.app.validator.validate("skills", payload)
            path = os.path.join(self.app.data_dir, "skills.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            # Reload runtime SkillDB
            from pathlib import Path as _P
            self.app.skills = self.app.data_manager.load_skills(_P(self.app.data_dir) / "skills.json")
            self.app.load_data_dir(self.app.data_dir)
            messagebox.showinfo("Saved", "Skills saved.")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()