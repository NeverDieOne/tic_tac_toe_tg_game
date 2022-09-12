# Tic Tac Toe Game for TG

Игра крестики-нолики для телеграма.

## Установка зависимостей

```console
pip install -r requirements.txt
```

## Установка зависимостей для разработки

```console
pip install -r requirements_dev.txt
```

## Запуск бота

```console
python main.py
```

## Переменные окружения

```text
TELEGRAM_BOT_TOKEN='токен телеграм бота, можно получить у BotFather'
REDIS_HOST='хост для подключения к редису'
REDIS_PORT='порт для подключения к редису'
REDIS_DB_USER='номер БД в редисе для пользователей'
REDIS_DB_GAME='номер БД в редисе для игр'
```

## IN PROGRESS

- [X] Создание игры
- [X] Приглашение игрока в игру
- [X] Синхронизация полей

## TODO

- [ ] Игра с ИИ
- [ ] Рейтинговая игра с рандомными игроками
