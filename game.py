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
    participants_messages_ids: set[tuple[int, int]] = set()
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
    
    def is_cell_empty(self, row: int, button: int) -> bool:
        return not self.field[row][button]

    def set_sell(self, row: int, button: int, symbol: str) -> None:
        self.field[row][button] = symbol

    def is_winner(self, symbol: str) -> bool: 
        return any([
            set([self.field[0][0], self.field[1][1], self.field[2][2]]) == set([symbol]),
            set([self.field[2][0], self.field[1][1], self.field[0][2]]) == set([symbol]),
            set([self.field[0][0], self.field[1][0], self.field[2][0]]) == set([symbol]),
            set([self.field[0][1], self.field[1][1], self.field[2][1]]) == set([symbol]),
            set([self.field[0][2], self.field[1][2], self.field[2][2]]) == set([symbol]),
            set(self.field[0]) == set([symbol]),
            set(self.field[1]) == set([symbol]),
            set(self.field[2]) == set([symbol]),
        ])
         
