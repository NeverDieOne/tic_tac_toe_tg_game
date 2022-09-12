import asyncio
import json
import logging
from enum import Enum, auto
from textwrap import dedent

from aioredis import Redis
from environs import Env
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes, ConversationHandler, MessageHandler,
                          filters)

from game import Game, GameStates
from field import get_field_buttons

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
    user_db: Redis = context.bot_data['user_db']
    game_db: Redis = context.bot_data['game_db']

    user_id = update.effective_user.id  # type: ignore
    chat_id = update.effective_chat.id  # type: ignore
    message_id = context.user_data['message_id']  # type: ignore
    
    if game_id := await user_db.get(user_id):  # type: ignore
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=dedent(f"""\
                Вы уже находитесь в игре: {game_id}
                Присоединяйтесь к ней!
            """)
        )
        await context.bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                'Подключиться к игре',
                callback_data='connect_to_game')
            ]])
        )
        return States.MENU
    
    game_id = await game_db.incr('_id')
    new_game = Game(
        id=game_id,
        state=GameStates.PLAYER_WAITING,
        participants=[user_id],
        current_player=user_id,
    )

    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=dedent(f"""
            ID игры: {game_id}
            Текущий ход у вас
        """),
    )
    await context.bot.edit_message_reply_markup(
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=get_field_buttons(new_game.field)
    )

    new_game.participants_messages_ids.add(message_id)
    await game_db.set(game_id, new_game.json())
    await user_db.set(f'{user_id}_game', new_game.id)

    return States.IN_GAME
    

async def join_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> States:
    game_db: Redis = context.bot_data['game_db']
    user_db: Redis = context.bot_data['user_db']

    user_id = update.effective_user.id  # type: ignore
    chat_id = update.effective_chat.id  # type: ignore
    message_id = context.user_data['message_id']  # type: ignore

    if update.callback_query:
        await context.bot.edit_message_text(
            text='Введите ID игры для подключения',
            message_id=message_id,
            chat_id=chat_id
        )
        return States.JOIN_GAME
    else:
        game_id = update.effective_message.text  # type: ignore
        user_game_id = await user_db.get(user_id)  # type: ignore

        if user_game_id and user_game_id != game_id:
            await context.bot.edit_message_text(
                text=f'У вас уже есть игра: {user_game_id}',
                message_id=message_id,
                chat_id=chat_id
            )
            await context.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
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

        game_info = await game_db.get(game_id)
        if not game_info:
            await context.bot.edit_message_text(
                text=f'Игры с ID {game_id} не существует, введите другой ID',
                message_id=message_id,
                chat_id=chat_id
            )
            return States.JOIN_GAME
        
        game = Game(**json.loads(game_info))
        if len(game.participants) == 2 and user_id not in game.participants:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text='В игре уже достаточно игроков, вы не можете присоединиться'
            )
            return States.JOIN_GAME
        
        if user_id not in game.participants:
            game.participants.append(user_id)

        await user_db.set(f'{user_id}_game', game.id)

        current_move = 'у вас' if game.current_player == user_id else 'у соперника' 
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=dedent(f"""\
                Вы присоединилсь к игре: {game_id}
                Текущий ход: {current_move}
            """)
        )
        await context.bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=get_field_buttons(game.field)
        )

        game.participants_messages_ids.add(message_id)
        await game_db.set(game_id, game.json())

        return States.IN_GAME

    
async def make_move(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> States:

    logger.info(update.callback_query)
    logger.info('User make move')
    return States.IN_GAME
        

async def flush_db(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_db: Redis = context.bot_data['user_db']
    game_db: Redis = context.bot_data['game_db']

    await user_db.flushdb()
    await game_db.flushdb()


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )

    env = Env()
    env.read_env()

    application = Application.builder().token(env.str('TELEGRAM_BOT_TOKEN')).build()
    application.bot_data['game_db'] = Redis(
        host=env.str('REDIS_HOST'),
        port=env.int('REDIS_PORT'),
        db=env.int('REDIS_DB_GAME'),
        decode_responses=True,
    )

    application.bot_data['user_db'] = Redis(
        host=env.str('REDIS_HOST'),
        port=env.int('REDIS_PORT'),
        db=env.int('REDIS_DB_USER'),
        decode_responses=True,
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            States.MENU: [
                CallbackQueryHandler(create_game, pattern='new_game'),
                CallbackQueryHandler(join_game, pattern='connect_to_game')
            ],
            States.IN_GAME: [
                CallbackQueryHandler(make_move, r'\d{2}')
            ],
            States.JOIN_GAME: [
                MessageHandler(filters.TEXT, join_game)
            ]
        },
        fallbacks=[],
        allow_reentry=True
    )
    
    application.add_handler(CommandHandler('flush', flush_db))
    application.add_handler(conv_handler)
    application.run_polling()

    asyncio.run(application.bot_data['user_db'].close())
    asyncio.run(application.bot_data['game_db'].close())


if __name__ == '__main__':
    main()

