from enum import Enum, auto
from typing import Any

from pydantic import BaseModel, validator


class GameStates(Enum):
    PLAYER_WAITING = auto()
    IN_PROGRESS = auto()
    FINISHED = auto()


class Game(BaseModel):
    id: int
    state: GameStates
    participants: list[int] = []
    current_player: int | None = None
    field: list[list[str | None]] = [
        [None, None, None],
        [None, None, None],
        [None, None, None]
    ]

    @validator('participants')
    def participants_len(cls, v: list[int]) -> list[int]:
        if len(v) > 2:
            raise ValueError('Game can contain only 2 participants')
        return v
    
    @validator('current_player')
    def player_in_participants(
        cls,
        v: int,
        values: dict[Any, Any],
        **kwargs: dict[Any, Any]
    ) -> int:
        if v and 'participants' in values and v not in values['participants']:
            raise ValueError('Only participant can be a player')
        return v
