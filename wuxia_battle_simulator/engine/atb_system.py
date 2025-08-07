from typing import List, Optional
from dataclasses import dataclass


@dataclass
class _ActorView:
    actor_id: str
    agility: int
    time_units: float


class ATBClock:
    """
    Simple ATB clock for MVP.
    - Each tick accumulates time_units += agility * tick_scale.
    - When any actor reaches threshold (>= threshold), returns that actor_id for action.
    - Tie-breaking: deterministic by actor_id ascending.
    """
    def __init__(self, threshold: int = 100, tick_scale: float = 1.0) -> None:
        self.threshold = threshold
        self.tick_scale = tick_scale
        self._now: float = 0.0

    def reset(self) -> None:
        self._now = 0.0

    def current_time(self) -> float:
        return self._now

    def tick(self, actors: List[_ActorView]) -> Optional[str]:
        """
        Performs one accumulation cycle. Returns actor_id ready to act or None.
        """
        self._now += 1.0
        ready: List[_ActorView] = []
        for a in actors:
            a.time_units += a.agility * self.tick_scale
            if a.time_units >= self.threshold:
                ready.append(a)

        # If none ready yet, continue ticking until someone is ready to act.
        # This guarantees progress for small agility values.
        guard = 0
        while not ready and guard < 1000:
            for a in actors:
                a.time_units += a.agility * self.tick_scale
                if a.time_units >= self.threshold and a not in ready:
                    ready.append(a)
            guard += 1
            self._now += 1.0
        if not ready:
            return None

        # Deterministic tie-break by actor_id (higher accumulated time wins, then id)
        ready.sort(key=lambda x: (x.time_units, x.actor_id))
        chosen = ready[-1]
        # Consume threshold for the selected actor
        chosen.time_units -= self.threshold
        return chosen.actor_id