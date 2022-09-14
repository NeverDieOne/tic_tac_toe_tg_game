import json
import logging
from enum import Enum, auto
from pathlib import Path
from textwrap import dedent

from environs import Env
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes, ConversationHandler, MessageHandler,
                          PicklePersistence, filters)

from field import get_field_buttons
from game import Game, GameStates, Player


logger = logging.getLogger(__name__)


class States(Enum):
    MENU = auto()
    IN_GAME = auto()
    JOIN_GAME = auto()


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> States:
    message = await update.message.reply_text(
        text=dedent("""\
            Приветствую тебя в игре крестики-нолики.
            Ты хочешь создать новую игру или подключиться к существующей?
        """),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('Создать игру', callback_data='new_game')],
            [InlineKeyboardButton(
                'Подключиться к игре', callback_data='connect_to_game'
            )]
        ])
    )
    context.user_data.update({'message_id': message.id})  # type: ignore
    return States.MENU


async def create_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> States:
    message_id = context.user_data['message_id']  # type: ignore
    chat_id = update.effective_chat.id  # type: ignore
    user_id = update.effective_user.id  # type: ignore
    first_name = update.effective_user.first_name  # type: ignore
    user_name = update.effective_user.username  # type: ignore
    bot = await context.bot.get_me()
    
    if game_id := context.user_data.get('current_game_id'):  # type: ignore
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=dedent(f"""\
                Ты уже находишься в игре: {game_id}
                Присоединяйся к ней!
            """),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                'Подключиться к игре',
                callback_data='connect_to_game')
            ]])
        )
        return States.MENU
    
    last_game_id = context.bot_data.get('_id') or 0
    game_id = last_game_id + 1
    context.bot_data['_id'] = game_id
    new_player = Player(
        user_id=user_id,
        chat_id=chat_id,
        first_name=f'{first_name} ({user_name})',
        message_id=message_id,
        symbol='X'
    )
    new_game = Game(
        id=game_id,
        state=GameStates.PLAYER_WAITING,
        participants=[new_player],
        current_player=new_player,
        deeplink=f'https://t.me/{bot.username}?start={game_id}'
    )

    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=new_game.generate_message(),
        reply_markup=InlineKeyboardMarkup(get_field_buttons(new_game.field))
    )

    context.bot_data[game_id] = new_game.json()
    context.user_data['current_game_id'] = new_game.id  # type: ignore

    return States.IN_GAME
    

async def join_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> States:
    user_id = update.effective_user.id  # type: ignore
    chat_id = update.effective_chat.id  # type: ignore
    message_id = context.user_data['message_id']  # type: ignore
    first_name = update.effective_user.first_name  # type: ignore
    user_name = update.effective_user.username  # type: ignore

    if update.callback_query:
        await context.bot.edit_message_text(
            text='Введи ID игры для подключения',
            message_id=message_id,
            chat_id=chat_id
        )
        return States.JOIN_GAME
    else:
        game_id = int(update.effective_message.text)  # type: ignore
        user_game_id = context.user_data.get('current_game_id')  # type: ignore

        if user_game_id and user_game_id != game_id:
            await context.bot.edit_message_text(
                text=f'У тебя уже есть игра: {user_game_id}',
                message_id=message_id,
                chat_id=chat_id,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                    'Подключиться к игре',
                    callback_data='connect_to_game')
                ]])
            )
            return States.JOIN_GAME
        
        await context.bot.delete_message(
            chat_id=chat_id,
            message_id=update.effective_message.id  # type: ignore
        )

        game_info = context.bot_data.get(game_id)
        if not game_info:
            await context.bot.edit_message_text(
                text=f'Игры с ID {game_id} не существует, введи другой ID',
                message_id=message_id,
                chat_id=chat_id,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                    text='Создать игру', callback_data='new_game'
                )]])
            )
            return States.JOIN_GAME
        
        game = Game(**json.loads(game_info))
        if (
            len(game.participants) == 2 and
            user_id not in [p.user_id for p in game.participants]
        ):
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text='В игре уже достаточно игроков, ты не можешь присоединиться',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                    text='Создать игру', callback_data='new_game'
                )]])
            )
            return States.JOIN_GAME

        if game.state in [GameStates.FINISHED, GameStates.DRAW]:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text='Игра завершена. Ты не можешь к ней присоединиться',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                    text='Создать игру', callback_data='new_game'
                )]])
            )
            return States.JOIN_GAME
        
        player = Player(
            user_id=user_id,
            chat_id=chat_id,
            first_name=f'{first_name} ({user_name})',
            message_id=message_id,
            symbol='O' if game.participants else 'X'
        )
        if player.user_id not in [p.user_id for p in game.participants]:
            game.participants.append(player)
            game.state = GameStates.IN_PROGRESS

        context.user_data['current_game_id'] = game.id  # type: ignore
    
        for player in game.participants:
            await context.bot.edit_message_text(
                chat_id=player.chat_id,
                message_id=player.message_id,
                text=game.generate_message(),
                reply_markup=InlineKeyboardMarkup(
                    get_field_buttons(game.field)
                )
            )

        context.bot_data[game_id] = game.json()
        return States.IN_GAME

    
async def make_move(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> States:
    user_id = update.effective_user.id  # type: ignore
    game_id = context.user_data.get('current_game_id')  # type: ignore
    game: Game = Game(**json.loads(context.bot_data[game_id]))

    if game.state in [GameStates.FINISHED, GameStates.DRAW]:
        await update.callback_query.answer('Игра окончена')
        return States.IN_GAME

    if len(game.participants) != 2:
        await update.callback_query.answer('Ты не можете начать игру один!')
        return States.IN_GAME

    if game.current_player.user_id != user_id:
        await update.callback_query.answer('Сейчас не твой ход')
        return States.IN_GAME
    
    row, button = [int(_) for _ in list(update.callback_query.data)]
    if game.field[row][button]:
        await update.callback_query.answer('Сюда нельзя ничего ставить')
        return States.IN_GAME

    game.field[row][button] = game.current_player.symbol

    is_draw = all([all(row) for row in game.field])
    has_winner = game.is_winner(game.current_player.symbol)
    if is_draw:
        game.winner = 'ничья'
        game.state = GameStates.DRAW
    if has_winner:
        game.winner = game.current_player.first_name
        game.state = GameStates.FINISHED
    if not has_winner and not is_draw:
        next_player = [p for p in game.participants if p.user_id != user_id][0]
        game.current_player = next_player
        game.state = GameStates.IN_PROGRESS

    context.bot_data[game_id] = game.json()
    for player in game.participants:
        await context.bot.edit_message_text(
            chat_id=player.chat_id,
            message_id=player.message_id,
            text=game.generate_message(),
            reply_markup=InlineKeyboardMarkup(get_field_buttons(game.field))
        )

    return States.IN_GAME


async def remove_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> States:
    chat_id = update.effective_chat.id  # type: ignore
    game_id = context.user_data['current_game_id']  # type: ignore
    game: Game = Game(**json.loads(context.bot_data[game_id]))
    
    for player in game.participants.copy():
        if player.chat_id == chat_id:
            game.participants.remove(player)

    message = await context.bot.send_message(
        chat_id=chat_id,
        text='Выбирай что хочешь сделать:',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('Создать игру', callback_data='new_game')],
            [InlineKeyboardButton(
                'Подключиться к игре', callback_data='connect_to_game'
            )]
        ])
    )

    del context.user_data['current_game_id']  # type: ignore
    context.user_data['message_id'] = message.id  # type: ignore

    return States.MENU


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )
    data_path = Path('data')
    data_path.mkdir(exist_ok=True)

    env = Env()
    env.read_env()

    builder = Application.builder()
    application = builder.token(env.str('TELEGRAM_BOT_TOKEN')).build()

    application.persistence = PicklePersistence(
        filepath=data_path / 'db.pickle'
    )
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            States.MENU: [
                CallbackQueryHandler(create_game, pattern='new_game'),
                CallbackQueryHandler(join_game, pattern='connect_to_game')
            ],
            States.IN_GAME: [
                CallbackQueryHandler(make_move, r'\d{2}'),
                CallbackQueryHandler(remove_game, 'back_to_menu')
            ],
            States.JOIN_GAME: [
                MessageHandler(filters.TEXT, join_game),
                CallbackQueryHandler(create_game, pattern='new_game')
            ]
        },
        fallbacks=[],
        allow_reentry=True,
        persistent=True,
        name='game_conversation'
    )

    application.add_handler(conv_handler)
    application.run_polling()


if __name__ == '__main__':
    main()
