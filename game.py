from enum import Enum
from textwrap import dedent

from pydantic import BaseModel, validator


class GameStates(Enum):
    PLAYER_WAITING = 'ожидание игроков'
    IN_PROGRESS = 'в процессе'
    FINISHED = 'завершена'
    DRAW = 'ничья'


class Player(BaseModel):
    user_id: int
    chat_id: int
    message_id: int | None = None
    first_name: str
    symbol: str


class Game(BaseModel):
    id: int
    state: GameStates
    winner: str | None = None
    current_player: Player
    participants: list[Player] = []
    field: list[list[str | None]] = [
        [None, None, None],
        [None, None, None],
        [None, None, None]
    ]
    deeplink: str

    @validator('participants')
    def participants_len(cls, v: list[int]) -> list[int]:
        if len(v) > 2:
            raise ValueError('Game can contain only 2 participants')
        return v

    def generate_message(self) -> str:
        message = dedent(f"""\
            Game ID: {self.id}
            Текущий ход: {self.current_player.first_name}
            Статус игры: {self.state.value}
            Победитель: {self.winner or ' '}
        """)

        if len(self.participants) < 2:
            message += dedent(f"""\
                Пригласи друга:
                {self.deeplink}
            """)

        return message

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
