from environs import Env
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters


async def echo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(update.message.text)
    

def main() -> None:
    env = Env()
    env.read_env()

    application = Application.builder().token(env.str('TELEGRAM_BOT_TOKEN')).build()

    application.add_handler(MessageHandler(filters.TEXT, echo_handler))

    application.run_polling()


if __name__ == '__main__':
    main()

