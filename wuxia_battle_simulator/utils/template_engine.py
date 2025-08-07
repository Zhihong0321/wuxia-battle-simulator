from typing import Dict, Any
import re
from .logger import get_logger
from wuxia_battle_simulator.narrator.variable_resolver import VariableResolver

_PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")

class TemplateEngine:
    """
    Lightweight template formatter that supports:
      - {dot.path}
      - {array[0]}
    Missing variables resolve to "" and log a warning.
    """
    def __init__(self, resolver: VariableResolver) -> None:
        self._resolver = resolver
        self._log = get_logger()

    def format(self, template: str, context: Dict[str, Any]) -> str:
        def repl(m: re.Match) -> str:
            path = m.group(1).strip()
            val = self._resolver.resolve(path, context)
            if val == "" and path not in context:
                self._log.debug(f"Template var missing: {path}")
            return str(val)
        return _PLACEHOLDER_RE.sub(repl, template)

    # Alias expected by tests
    def render(self, template: str, context: Dict[str, Any]) -> str:
        return self.format(template, context)