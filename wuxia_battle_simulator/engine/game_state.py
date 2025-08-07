from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class Stats:
    strength: int
    agility: int
    defense: int
    max_hp: int
    max_qi: int


@dataclass
class EquippedSkill:
    skill_id: str
    tier: int


@dataclass
class CharacterState:
    id: str
    name: str
    faction: str
    faction_terminology: Dict[str, str]
    stats: Stats
    hp: int
    qi: int
    cooldowns: Dict[str, int] = field(default_factory=dict)  # skill_id -> remaining turns
    skills: List[EquippedSkill] = field(default_factory=list)
    time_units: float = 0.0  # ATB accumulator

    def is_alive(self) -> bool:
        return self.hp > 0


class GameState:
    def __init__(self, characters: List[CharacterState]) -> None:
        self.characters: Dict[str, CharacterState] = {c.id: c for c in characters}

    def get_actor(self, actor_id: str) -> CharacterState:
        return self.characters[actor_id]

    def all_characters(self) -> List[CharacterState]:
        return list(self.characters.values())

    def living(self) -> List[CharacterState]:
        return [c for c in self.characters.values() if c.is_alive()]

    def get_opponents(self, actor_id: str) -> List[CharacterState]:
        # MVP: everyone not actor and alive is an opponent
        return [c for c in self.living() if c.id != actor_id]

    def apply_damage(self, target_id: str, amount: int) -> None:
        target = self.characters[target_id]
        amount = max(0, int(amount))
        target.hp = max(0, target.hp - amount)

    def consume_qi(self, actor_id: str, amount: int) -> None:
        actor = self.characters[actor_id]
        actor.qi = max(0, actor.qi - max(0, int(amount)))

    def set_cooldown(self, actor_id: str, skill_id: str, turns: int) -> None:
        actor = self.characters[actor_id]
        actor.cooldowns[skill_id] = max(0, int(turns))

    def decrement_cooldowns(self, actor_id: str) -> None:
        actor = self.characters[actor_id]
        for k in list(actor.cooldowns.keys()):
            actor.cooldowns[k] = max(0, actor.cooldowns[k] - 1)

    def is_battle_over(self) -> bool:
        # MVP: battle ends when only one or zero living remain
        return len(self.living()) <= 1

    def snapshot(self) -> Dict[str, Any]:
        return {
            "characters": {
                cid: {
                    "hp": c.hp,
                    "qi": c.qi,
                    "cooldowns": dict(c.cooldowns),
                    "time_units": c.time_units,
                }
                for cid, c in self.characters.items()
            }
        }