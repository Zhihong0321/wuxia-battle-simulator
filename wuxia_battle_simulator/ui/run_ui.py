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
        # Expand default width to 1200px; keep height flexible
        self.geometry("1200x700")
        self.minsize(1200, 600)

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

        # Basic fields (align with schema: stats requires hp,max_hp,qi,max_qi,strength,agility,defense)
        ttk.Label(form, text="ID").grid(row=0, column=0, sticky="e"); self.id_var = tk.StringVar(); ttk.Entry(form, textvariable=self.id_var, width=40).grid(row=0, column=1, sticky="w")
        ttk.Label(form, text="Name").grid(row=1, column=0, sticky="e"); self.name_var = tk.StringVar(); ttk.Entry(form, textvariable=self.name_var, width=40).grid(row=1, column=1, sticky="w")
        ttk.Label(form, text="Faction").grid(row=2, column=0, sticky="e"); self.faction_var = tk.StringVar(); ttk.Entry(form, textvariable=self.faction_var, width=40).grid(row=2, column=1, sticky="w")
        # Stats row 1
        ttk.Label(form, text="HP").grid(row=3, column=0, sticky="e"); self.hp_var = tk.IntVar(); ttk.Spinbox(form, from_=0, to=99999, textvariable=self.hp_var, width=8).grid(row=3, column=1, sticky="w")
        ttk.Label(form, text="Max HP").grid(row=3, column=2, sticky="e"); self.max_hp_var = tk.IntVar(); ttk.Spinbox(form, from_=1, to=99999, textvariable=self.max_hp_var, width=8).grid(row=3, column=3, sticky="w")
        # Stats row 2
        ttk.Label(form, text="QI").grid(row=4, column=0, sticky="e"); self.qi_var = tk.IntVar(); ttk.Spinbox(form, from_=0, to=99999, textvariable=self.qi_var, width=8).grid(row=4, column=1, sticky="w")
        ttk.Label(form, text="Max QI").grid(row=4, column=2, sticky="e"); self.max_qi_var = tk.IntVar(); ttk.Spinbox(form, from_=0, to=99999, textvariable=self.max_qi_var, width=8).grid(row=4, column=3, sticky="w")
        # Stats row 3
        ttk.Label(form, text="Strength").grid(row=5, column=0, sticky="e"); self.str_var = tk.IntVar(); ttk.Spinbox(form, from_=0, to=9999, textvariable=self.str_var, width=8).grid(row=5, column=1, sticky="w")
        ttk.Label(form, text="Agility").grid(row=5, column=2, sticky="e"); self.agi_var = tk.IntVar(); ttk.Spinbox(form, from_=0, to=9999, textvariable=self.agi_var, width=8).grid(row=5, column=3, sticky="w")
        ttk.Label(form, text="Defense").grid(row=5, column=4, sticky="e"); self.def_var = tk.IntVar(); ttk.Spinbox(form, from_=0, to=9999, textvariable=self.def_var, width=8).grid(row=5, column=5, sticky="w")
        # Skills
        ttk.Label(form, text="Skills (skill_id:tier, comma-separated)").grid(row=6, column=0, sticky="e"); self.skills_var = tk.StringVar(); ttk.Entry(form, textvariable=self.skills_var, width=40).grid(row=6, column=1, columnspan=5, sticky="w")

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
        # Populate stats with full schema coverage
        self.hp_var.set(int(stats.get("hp", stats.get("max_hp", 100))))
        self.max_hp_var.set(int(stats.get("max_hp", max(1, int(stats.get("hp", 100))))))
        self.qi_var.set(int(stats.get("qi", stats.get("max_qi", 100))))
        self.max_qi_var.set(int(stats.get("max_qi", max(0, int(stats.get("qi", 100))))))
        self.str_var.set(int(stats.get("strength", 10)))
        self.agi_var.set(int(stats.get("agility", 10)))
        self.def_var.set(int(stats.get("defense", 10)))
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
        # Build schema-compliant character dict
        stats = {
            "hp": int(self.hp_var.get()),
            "max_hp": int(self.max_hp_var.get() or self.hp_var.get()),
            "qi": int(self.qi_var.get()),
            "max_qi": int(self.max_qi_var.get() or self.qi_var.get()),
            "strength": int(self.str_var.get()),
            "agility": int(self.agi_var.get()),
            "defense": int(self.def_var.get()),
        }
        return {
            "id": self.id_var.get().strip(),
            "name": self.name_var.get().strip(),
            "faction": self.faction_var.get().strip(),
            "stats": stats,
            "skills": skills
        }

    def new_character(self):
        new = {
            "id":"new_char",
            "name":"新角色",
            "faction":"",
            "stats":{"hp":100,"max_hp":100,"qi":100,"max_qi":100,"strength":10,"agility":10,"defense":10},
            "skills":[]
        }
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
        # internal state for grid editing
        self._editing = {"row": None, "column": None}

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
        # Ensure body expands columns properly with 1200px width
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=2)

        ttk.Label(form, text="ID").grid(row=0, column=0, sticky="e"); self.id_var = tk.StringVar(); ttk.Entry(form, textvariable=self.id_var, width=40).grid(row=0, column=1, sticky="w")
        ttk.Label(form, text="Name").grid(row=1, column=0, sticky="e"); self.name_var = tk.StringVar(); ttk.Entry(form, textvariable=self.name_var, width=40).grid(row=1, column=1, sticky="w")
        ttk.Label(form, text="Type").grid(row=2, column=0, sticky="e"); self.type_var = tk.StringVar(); ttk.Entry(form, textvariable=self.type_var, width=40).grid(row=2, column=1, sticky="w")

        # Tiers grid with per-cell validation
        ttk.Label(form, text="Tiers").grid(row=3, column=0, sticky="ne")
        tiers_frame = ttk.Frame(form)
        tiers_frame.grid(row=3, column=1, sticky="nsew")
        # Make form column stretch
        form.grid_rowconfigure(3, weight=1)
        form.grid_columnconfigure(1, weight=1)

        # Include narrative_template column to satisfy schema and enable editing
        columns = ("tier","base_damage","hit_chance","crit_chance","qi_cost","cooldown","power_multiplier","tier_name","narrative_template")
        self.tiers_tree = ttk.Treeview(tiers_frame, columns=columns, show="headings", height=10)
        headings = {
            "tier":"tier","base_damage":"base_damage","hit_chance":"hit_chance","crit_chance":"crit_chance",
            "qi_cost":"qi_cost","cooldown":"cooldown","power_multiplier":"power_multiplier","tier_name":"tier_name",
            "narrative_template":"narrative_template"
        }
        for cid, text in headings.items():
            self.tiers_tree.heading(cid, text=text)
            # set reasonable widths for 1200px layout
            if cid == "narrative_template":
                width = 380
                anchor = "w"
            elif cid == "tier_name":
                width = 160
                anchor = "center"
            else:
                width = 90
                anchor = "center"
            self.tiers_tree.column(cid, width=width, anchor=anchor, stretch=True)
        self.tiers_tree.pack(fill="both", expand=True, side="left")

        # Scrollbar
        sb = ttk.Scrollbar(tiers_frame, orient="vertical", command=self.tiers_tree.yview)
        self.tiers_tree.configure(yscrollcommand=sb.set)
        sb.pack(fill="y", side="right")

        # Inline editor (Entry overlay) — support single-line editing; narrative_template opens a modal for multi-line
        self._edit_var = tk.StringVar()
        self._edit_entry = ttk.Entry(self.tiers_tree, textvariable=self._edit_var)
        self._edit_entry.bind("<Return>", lambda e: self._commit_cell_edit())
        self._edit_entry.bind("<Escape>", lambda e: self._cancel_cell_edit())
        # Commit edit when focus leaves the inline Entry (prevents value loss on mouse click)
        self._edit_entry.bind("<FocusOut>", lambda e: self._commit_cell_edit())
        # Begin edit on single click (more natural for grids) and double-click for safety
        self.tiers_tree.bind("<Button-1>", self._begin_cell_edit)
        self.tiers_tree.bind("<Double-1>", self._begin_cell_edit)

        # Helper validators
        def _is_int_ge(v: str, min_v: int) -> bool:
            try:
                return int(v) >= min_v
            except Exception:
                return False

        def _is_num_ge(v: str, min_v: float) -> bool:
            try:
                return float(v) >= min_v
            except Exception:
                return False

        def _is_prob(v: str) -> bool:
            try:
                x = float(v); return 0.0 <= x <= 1.0
            except Exception:
                return False

        self._validators = {
            "tier": lambda v: _is_int_ge(v, 1),
            "base_damage": lambda v: _is_num_ge(v, 0.0),
            "hit_chance": _is_prob,
            "crit_chance": _is_prob,
            "qi_cost": lambda v: _is_int_ge(v, 0),
            "cooldown": lambda v: _is_int_ge(v, 0),
            "power_multiplier": lambda v: True if v.strip()=="" else _is_num_ge(v, -float("inf")),
            "tier_name": lambda v: True,
            "narrative_template": lambda v: len(v.strip()) > 0
        }

        # Replace toolbar Add/Remove Tier to operate on grid as well
        # Buttons already exist in main toolbar; keep their commands

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
        # Populate tiers grid
        for row in self.tiers_tree.get_children():
            self.tiers_tree.delete(row)
        tiers = s.get("tiers", [])
        # stable sort by tier if present
        try:
            tiers = sorted(tiers, key=lambda t: int(t.get("tier", 0)))
        except Exception:
            pass
        for t in tiers:
            # support both nested 'parameters' (correct schema) and legacy flat fields
            p = t.get("parameters", t)
            values = (
                t.get("tier",""),
                p.get("base_damage",""),
                p.get("hit_chance",""),
                p.get("critical_chance",""),
                p.get("qi_cost",""),
                p.get("cooldown",""),
                p.get("power_multiplier",""),
                t.get("tier_name",""),
                t.get("narrative_template",""),
            )
            self.tiers_tree.insert("", "end", values=values)

    def _collect_form(self):
        # Collect from grid
        tiers = []
        for iid in self.tiers_tree.get_children():
            row = dict(zip(
                ("tier","base_damage","hit_chance","crit_chance","qi_cost","cooldown","power_multiplier","tier_name","narrative_template"),
                self.tiers_tree.item(iid,"values")
            ))
            # Cast numeric fields
            def _to_int(v):
                try: return int(v)
                except Exception: return 0
            def _to_float(v):
                try: return float(v)
                except Exception: return 0.0
            # Build schema-compliant tier with nested parameters
            tier_num = _to_int(row.get("tier","1"))
            params = {
                "base_damage": int(_to_float(row.get("base_damage","0"))),  # integer per validation schema
                "power_multiplier": max(0.0, _to_float(row.get("power_multiplier","0"))),  # min 0
                "qi_cost": _to_int(row.get("qi_cost","0")),
                "cooldown": _to_int(row.get("cooldown","0")),
                "hit_chance": _to_float(row.get("hit_chance","1")),
                "critical_chance": _to_float(row.get("crit_chance","0")),
            }
            tier_obj = {
                "tier": tier_num,
                "parameters": params,
                "tier_name": str(row.get("tier_name","")).strip(),
                "narrative_template": str(row.get("narrative_template","")),
            }
            tiers.append(tier_obj)
        # Sort tiers by tier ascending
        try:
            tiers.sort(key=lambda t: int(t.get("tier",0)))
        except Exception:
            pass
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
        # Add a new row to the grid with next tier number
        current_tiers = []
        for iid in self.tiers_tree.get_children():
            vals = self.tiers_tree.item(iid,"values")
            try:
                current_tiers.append(int(vals[0]))
            except Exception:
                pass
        next_tier = (max(current_tiers) + 1) if current_tiers else 1
        new_vals = (next_tier, 10, 1.0, 0.1, 0, 0, "", "", "")
        self.tiers_tree.insert("", "end", values=new_vals)

    def remove_tier(self):
        sel = self.listbox.curselection()
        if not sel: return
        # Remove selected grid row or last if none selected
        selection = self.tiers_tree.selection()
        if selection:
            for iid in selection:
                self.tiers_tree.delete(iid)
        else:
            children = self.tiers_tree.get_children()
            if children:
                self.tiers_tree.delete(children[-1])

    def save_current(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        # Commit any active cell edit before reading grid values
        if self._editing.get("row"):
            self._commit_cell_edit()
        # Validate grid values before updating in-memory model
        bad_msgs = []
        for iid in self.tiers_tree.get_children():
            vals = dict(zip(("tier","base_damage","hit_chance","crit_chance","qi_cost","cooldown","power_multiplier","tier_name","narrative_template"),
                            self.tiers_tree.item(iid,"values")))
            for k, fn in self._validators.items():
                if not fn(str(vals.get(k, "")).strip()):
                    bad_msgs.append(f"Invalid {k}='{vals.get(k)}' in row with tier={vals.get('tier')}")
        if bad_msgs:
            messagebox.showerror("Validation", "\n".join(bad_msgs))
            return
        # Update in-memory
        selected_index = sel[0]
        self._skills_raw[selected_index] = self._collect_form()
        # Persist immediately to disk to avoid data loss on exit
        try:
            payload = {"skills": self._skills_raw}
            self.app.validator.validate("skills", payload)
            path = os.path.join(self.app.data_dir, "skills.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            # Reload runtime SkillDB and datasets
            from pathlib import Path as _P
            self.app.skills = self.app.data_manager.load_skills(_P(self.app.data_dir) / "skills.json")
            current_name = self._skills_raw[selected_index].get("name","")
            self.app.load_data_dir(self.app.data_dir)
            # Refresh and restore selection
            self.refresh_list()
            if selected_index < self.listbox.size():
                self.listbox.selection_set(selected_index)
            else:
                for i, s in enumerate(self._skills_raw):
                    if s.get("name","") == current_name:
                        self.listbox.selection_set(i)
                        break
            messagebox.showinfo("Saved", "Skill saved to JSON.")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

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
    
    # ===== Inline cell editing handlers for tiers_tree =====
    def _treeview_identify_cell(self, event):
        # Identify row iid and column id under cursor
        region = self.tiers_tree.identify("region", event.x, event.y)
        if region != "cell":
            return None, None
        row_id = self.tiers_tree.identify_row(event.y)
        col_id = self.tiers_tree.identify_column(event.x)  # e.g. '#3'
        return row_id, col_id

    def _begin_cell_edit(self, event):
        # Commit any prior edit before starting a new one (prevents losing previous input)
        if self._editing.get("row"):
            self._commit_cell_edit()
        row_id, col_id = self._treeview_identify_cell(event)
        if not row_id or not col_id:
            return
        # Map col index to column name
        cols = self.tiers_tree["columns"]
        try:
            idx = int(col_id.replace("#","")) - 1
        except Exception:
            return
        if idx < 0 or idx >= len(cols):
            return
        colname = cols[idx]
        # narrative_template uses modal multiline editor
        if colname == "narrative_template":
            self._edit_narrative_modal(row_id, colname)
            return
        # Get bbox for overlay entry
        bbox = self.tiers_tree.bbox(row_id, col_id)
        if not bbox:
            return
        x, y, w, h = bbox
        # Pre-fill with current value
        values = list(self.tiers_tree.item(row_id, "values"))
        cur_val = values[idx] if idx < len(values) else ""
        self._edit_var.set(cur_val)
        self._edit_entry.place(x=x, y=y, width=w, height=h)
        self._edit_entry.focus_set()
        self._editing = {"row": row_id, "column": colname, "index": idx}

    def _commit_cell_edit(self):
        if not self._editing.get("row"):
            return
        val = self._edit_var.get()
        row_id = self._editing["row"]
        idx = self._editing["index"]
        colname = self._editing["column"]
        # Validate
        validator = self._validators.get(colname, lambda v: True)
        if not validator(val.strip()):
            messagebox.showerror("Validation", f"Invalid {colname}='{val}'")
            return
        values = list(self.tiers_tree.item(row_id, "values"))
        # Ensure list long enough
        while len(values) <= idx:
            values.append("")
        values[idx] = val
        self.tiers_tree.item(row_id, values=values)
        self._edit_entry.place_forget()
        self._editing = {"row": None, "column": None}

    def _cancel_cell_edit(self):
        self._edit_entry.place_forget()
        self._editing = {"row": None, "column": None}

    def _edit_narrative_modal(self, row_id, colname):
        # Modal dialog for multi-line editing of narrative_template
        top = tk.Toplevel(self)
        top.title("Edit narrative_template")
        top.transient(self.winfo_toplevel())
        top.grab_set()
        cols = self.tiers_tree["columns"]
        idx = cols.index(colname)
        cur_values = list(self.tiers_tree.item(row_id, "values"))
        cur_val = cur_values[idx] if idx < len(cur_values) else ""
        txt = tk.Text(top, width=60, height=8, wrap="word")
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        txt.insert("1.0", str(cur_val))
        btns = ttk.Frame(top)
        btns.pack(fill="x", padx=8, pady=(0,8))
        def on_ok():
            new_val = txt.get("1.0", "end-1c")
            if not self._validators["narrative_template"](new_val):
                messagebox.showerror("Validation", "narrative_template must be non-empty.")
                return
            cur_values[idx] = new_val
            self.tiers_tree.item(row_id, values=cur_values)
            top.destroy()
        def on_cancel():
            top.destroy()
        ttk.Button(btns, text="OK", command=on_ok).pack(side="right", padx=4)
        ttk.Button(btns, text="Cancel", command=on_cancel).pack(side="right")

def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()