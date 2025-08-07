from typing import Dict, Any
import random


class TextNarrator:
    """
    Supports per-skill, per-tier narrative templates embedded in skills (tier_narrative_template via context),
    while retaining compatibility with global templates.json if present.
    """
    def __init__(self, index, rng: random.Random, template_engine) -> None:
        self._index = index
        self._rng = rng
        self._engine = template_engine

    def get_default_template(self, narrative_type: str) -> Dict[str, Any]:
        # Simple defaults per narrative_type
        defaults = {
            "攻击": "{attacker}使出【{skill}】{tier_name}，攻向{target}！",
            "抵挡": "{target}凝神以对，化解来势。",
            "闪避": "{target}身形一闪，避过了攻击！",
            "暴击": "{attacker}一声怒喝，【{skill}】{tier_name}威势惊人，重创{target}！"
        }
        return {
            "id": "default_" + narrative_type,
            "narrative_type": narrative_type,
            "conditions": {},
            "template": defaults.get(narrative_type, "{attacker}出手了。"),
            "connective_phrases": ["随即", "说时迟那时快", "刹那间"]
        }

    def _choose_global_template_text(self, narrative_type: str, context: Dict[str, Any]) -> str:
        # Prefer new API if available; fall back to existing
        if hasattr(self._index, "select"):
            candidates = self._index.select(narrative_type, context)
        else:
            candidates = self._index.find_candidates(narrative_type, context)

        # Bias for early critical/high damage phrases (kept for compatibility)
        key_phrases = ("威力全开", "轰然袭至")
        chosen = None
        if candidates:
            if (narrative_type == "暴击" or context.get("critical")) and context.get("damage_percent") in ("high", "medium"):
                prioritized = [t for t in candidates if any(phrase in t.get("template", "") for phrase in key_phrases)]
                if prioritized:
                    prioritized.sort(key=lambda t: t.get("id", ""))
                    chosen = prioritized[0]

        if chosen is None:
            if candidates:
                chosen = self._rng.choice(candidates)
            else:
                chosen = self.get_default_template(narrative_type)
        return chosen.get("template", "")

    def render(self, context: Dict[str, Any]) -> str:
        narrative_type = context.get("narrative_type", "攻击")

        # 1) Use per-tier narrative from SkillDB if provided by engine mapping
        per_tier_tpl = (context.get("tier_narrative_template") or "").strip()
        if per_tier_tpl:
            text = per_tier_tpl
            # No connective phrase injection for per-tier authored lines to keep authorship intact
            rendered = self._engine.format(text, context)
            if context.get("critical"):
                rendered = f"{rendered}【暴击！】"
            return rendered

        # 2) Fallback to global templates.json
        text = self._choose_global_template_text(narrative_type, context)
        rendered = self._engine.format(text, context)

        # Keep legacy connective behavior in global mode only
        if self._rng.random() < 0.6 and isinstance(text, str) and "{attacker}" in text:
            # Use connective phrases from a synthetic default for flow
            prefix_candidates = ["随即", "说时迟那时快", "刹那间"]
            prefix = self._rng.choice(prefix_candidates)
            rendered = f"{prefix}，{rendered}"

        # Append fixed critical tag when requested
        if context.get("critical"):
            rendered = f"{rendered}【暴击！】"
        return rendered