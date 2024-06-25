# Rebotica AI Telegram Bot

Этот Telegram-бот создан для помощи пользователям в выборе IT-карьеры или профессии в цифровой экономике. 
Бот взаимодействует с пользователями через серию вопросов и предоставляет рекомендации на основе их ответов.

## Особенности

- Взаимодействие с пользователями через текстовые сообщения и инлайн-клавиатуру
- Административная панель для управления разрешенными пользователями и просмотра диалогов пользователей
- Логирование сообщений пользователей и ответов бота
- Интеграция с GPT-4 от OpenAI для генерации ответов
- Использование FAISS для поиска по сходству документов

## Необходимые условия

- Python 3.8+
- Токен Telegram-бота
- API-ключ OpenAI
- Переменные окружения, настроенные в файле `.env`

## Установка

1. **Клонируйте репозиторий:**

    ```bash
    git clone https://github.com/Voislav-Vpotoke/ReboticaAI.git
    cd ReboticaAI
    ```

2. **Создайте и активируйте виртуальную среду:**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3. **Установите зависимости:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Создайте файл `.env` и настройте переменные окружения:**

    ```env
    YOUR_BOT_TOKEN=your_telegram_bot_token
    YOUR_API_KEY=your_openai_api_key
    ADMIN_USERNAMES=admin1,admin2
    ```

5. **Инициализация базы данных:**

    База данных будет автоматически инициализирована при первом запуске бота.

## Использование

1. **Запустите бота:**

    ```bash
    python main.py
    ```

2. **Команды администратора:**

    - `/admin`: Открывает панель администратора с опциями для добавления или удаления пользователей, просмотра диалогов, удаления сообщений и списка пользователей.

3. **Взаимодействие с пользователями:**

    Пользователи могут начать взаимодействие с ботом, отправив команду `/start`. Бот задаст серию вопросов и предоставит рекомендации по карьере на основе ответов.

## Обзор кода

- **main.py**: Основной скрипт, содержащий функционал бота.
- **Функции работы с базой данных**: Функции для логирования сообщений, получения диалогов и управления разрешенными пользователями.
- **Обработчики Telegram**: Функции для обработки входящих сообщений, команд администратора и отправки ответов.
- **Интеграция с OpenAI**: Использование GPT-4 от OpenAI для генерации ответов на вопросы пользователей.
- **Интеграция с FAISS**: Для поиска релевантных отрывков документов на основе запросов пользователей.

## Логирование

Логи сохраняются в файл `bot.log` с политикой ротации по 1 МБ на файл.

## Лицензия

Этот проект лицензирован под MIT License. Подробности см. в файле LICENSE.
