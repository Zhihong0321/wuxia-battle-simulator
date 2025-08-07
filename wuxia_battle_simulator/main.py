import json
import sys
from pathlib import Path
from typing import Optional

# Entrypoint wiring for MVP scaffold (Python 3.9)
# Note: Modules referenced are stubs created in this scaffold.
# Ensure package-relative imports by using absolute package paths.

def _project_root() -> Path:
    return Path(__file__).resolve().parent

def _data_dir() -> Path:
    return _project_root() / "data"

def _load_config(config_path: Path) -> dict:
    if not config_path.exists():
        # Minimal default config
        return {
            "rng_seed": 42,
            "atb_threshold": 100,
            "atb_tick_scale": 1.0,
            "ui": {"speed": 1.0}
        }
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)

def main(argv: Optional[list] = None) -> int:
    argv = argv or sys.argv[1:]
    root = _project_root()
    data_dir = _data_dir()
    config = _load_config(data_dir / "config.json")

    # Deferred imports to allow running even if modules are not fully implemented yet
    from wuxia_battle_simulator.utils.logger import get_logger
    from wuxia_battle_simulator.validation.validator import Validator
    from wuxia_battle_simulator.utils.data_loader import DataManager
    from wuxia_battle_simulator.engine.atb_system import ATBClock
    from wuxia_battle_simulator.engine.game_state import GameState
    from wuxia_battle_simulator.engine.ai_policy import HeuristicAI
    from wuxia_battle_simulator.engine.battle_simulator import BattleSimulator
    from wuxia_battle_simulator.narrator.text_narrator import TextNarrator
    from wuxia_battle_simulator.narrator.template_index import TemplateIndex
    from wuxia_battle_simulator.utils.template_engine import TemplateEngine
    from wuxia_battle_simulator.narrator.variable_resolver import VariableResolver

    log = get_logger()

    # Initialize validation and data manager
    validator = Validator(root / "validation" / "schemas")
    dm = DataManager(validator)

    # Load data
    try:
        characters = dm.load_characters(data_dir / "characters.json")
        skills_db = dm.load_skills(data_dir / "skills.json")
        templates = dm.load_templates(data_dir / "templates.json")
    except Exception as e:
        log.error(f"Data loading failed: {e}")
        return 1

    # Build game state
    try:
        state: GameState = dm.build_game_state(characters)
    except Exception as e:
        log.error(f"Game state build failed: {e}")
        return 1

    # Seeded RNG
    import random
    rng_seed = config.get("rng_seed", 42)
    rng = random.Random(rng_seed)

    # Engine wiring
    clock = ATBClock(threshold=int(config.get("atb_threshold", 100)),
                     tick_scale=float(config.get("atb_tick_scale", 1.0)))
    ai = HeuristicAI(rng=rng, skills_db=skills_db)

    # Narrator wiring
    index = TemplateIndex(templates=templates)
    resolver = VariableResolver()
    templ_engine = TemplateEngine(resolver=resolver)
    narrator = TextNarrator(index=index, rng=rng, template_engine=templ_engine)

    simulator = BattleSimulator(state=state, ai=ai, clock=clock, rng=rng)

    # Optional: simple CLI run (UI will be added later)
    events = simulator.run_to_completion(max_steps=200)
    # Ensure UTF-8 output on Windows consoles that default to cp1252/gbk
    out = getattr(sys, "stdout", None)
    if out and hasattr(out, "reconfigure"):
        try:
            out.reconfigure(encoding="utf-8")
        except Exception:
            pass
    for ev in events:
        text = narrator.render(simulator.map_event_for_narration(ev))
        try:
            print(text)
        except UnicodeEncodeError:
            # Fallback: encode to utf-8 bytes then decode ignoring errors
            sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="ignore"))

    log.info("Simulation complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())