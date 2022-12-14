from telegram import InlineKeyboardButton


def get_field_buttons(
    fields: list[list[str | None]]
) -> list[list[InlineKeyboardButton]]:
    markup: list[list[InlineKeyboardButton]] = []

    for row_index, row in enumerate(fields):
        row_buttons: list[InlineKeyboardButton] = []
        for button_index, button in enumerate(row):
            button_text = button or ' '
            row_buttons.append(InlineKeyboardButton(
                text=button_text,
                callback_data=f'{row_index}{button_index}'
            ))
        
        markup.append(row_buttons)

    markup.append([
        InlineKeyboardButton('Выйти из игры', callback_data='back_to_menu')
    ])

    return markup
