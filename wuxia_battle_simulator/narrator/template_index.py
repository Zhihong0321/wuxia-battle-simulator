from typing import List, Dict, Any


class TemplateIndex:
    """
    Indexes templates by narrative_type and supports condition-based filtering.
    Conditions supported:
      - hit: bool (exact)
      - critical: bool (exact)
      - damage_percent: "low" | "medium" | "high" (exact) OR comparison string like "<10", ">=10", "<=25"
      - actor_faction: str (exact)
      - target_faction: str (exact)
    """
    def __init__(self, templates: List[Dict[str, Any]]) -> None:
        self._by_type: Dict[str, List[Dict[str, Any]]] = {}
        for t in templates or []:
            nt = t.get("narrative_type", "")
            self._by_type.setdefault(nt, []).append(t)

    # Backward-compatible API used by TextNarrator
    def find_candidates(self, narrative_type: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self.select(narrative_type, context)

    # New API expected by tests
    def select(self, narrative_type: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        candidates = self._by_type.get(narrative_type, [])
        out: List[Dict[str, Any]] = []
        for tpl in candidates:
            cond = tpl.get("conditions", {}) or {}
            if self._matches(cond, context):
                out.append(tpl)
        return out

    @staticmethod
    def _matches(cond: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
        for key, expected in cond.items():
            if key == "damage_percent":
                # expected may be bucket string or comparison string
                actual_ratio = ctx.get("damage_percent", None)
                # Allow both textual buckets and raw numeric ratio/percent in context:
                # If context provides numeric percent (0-100) or ratio (0-1), handle comparisons.
                if isinstance(expected, str) and expected and expected[0] in "<>=":
                    # normalize context numeric
                    val = ctx.get("damage_percent", None)
                    if val is None:
                        return False
                    # If context holds bucket string like "low/medium/high", cannot compare; fail
                    if isinstance(val, str):
                        return False
                    # If val seems like ratio (<=1.0), convert to percent
                    if isinstance(val, (int, float)) and val <= 1.0:
                        percent = float(val) * 100.0
                    else:
                        percent = float(val)
                    expr = expected.strip()
                    try:
                        if expr.startswith(">="):
                            if not (percent >= float(expr[2:].strip())):
                                return False
                        elif expr.startswith("<="):
                            if not (percent <= float(expr[2:].strip())):
                                return False
                        elif expr.startswith(">"):
                            if not (percent > float(expr[1:].strip())):
                                return False
                        elif expr.startswith("<"):
                            if not (percent < float(expr[1:].strip())):
                                return False
                        else:
                            # unsupported comparator; fallback to equality
                            if percent != float(expr):
                                return False
                    except Exception:
                        return False
                else:
                    # Require exact match for bucket strings
                    if ctx.get("damage_percent") != expected:
                        return False
            else:
                if key not in ctx:
                    return False
                if ctx[key] != expected:
                    return False
        return True