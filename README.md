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
```

## Запуск с помощью Dockerfile

Сборка имейджа:
```console
docker build -t tictac:latest .
```

Запуск имейджа:
```console
docker run --name=tictac --env-file={.env} --volume={data_path}:/app/data --restart=always -d tictac:latest
```

## IN PROGRESS

- [ ] Обновление класса Game до более самостоятельного

## TODO

- [ ] Тесты для проекта
- [ ] Игра с ИИ
- [ ] Рейтинговая игра с рандомными игроками
