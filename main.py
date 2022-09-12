import logging
from enum import Enum, auto
from textwrap import dedent

from environs import Env
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    ConversationHandler, CallbackQueryHandler, MessageHandler, filters
)

logger = logging.getLogger(__name__)


class States(Enum):
    MENU = auto()
    IN_GAME = auto()
    JOIN_GAME = auto()


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> States:
    await update.message.reply_text(
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
    return States.MENU


async def create_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> States:
    logger.info('In create game')
    return States.IN_GAME
    

async def join_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> States:
    if update.callback_query:
        await context.bot.send_message(
            text='Введите ID игры для подключения',
            chat_id=update.effective_chat.id  # type: ignore
        )
        return States.JOIN_GAME
    else:
        logger.info('In join game')
        return States.IN_GAME


def main() -> None:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO
    )

    env = Env()
    env.read_env()

    application = Application.builder().token(env.str('TELEGRAM_BOT_TOKEN')).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            States.MENU: [
                CallbackQueryHandler(create_game, pattern='new_game'),
                CallbackQueryHandler(join_game, pattern='connect_to_game')
            ],
            States.IN_GAME: [],
            States.JOIN_GAME: [
                MessageHandler(filters.TEXT, join_game)
            ]
        },
        fallbacks=[]
    )
    
    application.add_handler(conv_handler)
    application.run_polling()


if __name__ == '__main__':
    main()

