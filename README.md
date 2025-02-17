# AIogram Bot Template

Это шаблон для создания Telegram-бота с использованием библиотек:
- [aiogram 3.x.x](https://github.com/aiogram/aiogram)
- [aiogram_dialog](https://github.com/Tishka17/aiogram_dialog)
- [aiogram_i18n](https://github.com/aiogram/i18n)
- [arq](https://github.com/python-arq/arq)

а также поддержки Redis и многоязычности (i18n).
Шаблон предоставляет базовую структуру проекта,
включающую работу с планировщиком задач, конфигурацию через переменные окружения и пример
использования systemd для автозапуска на сервере.

## Особенности

- Базовая структура: четкое разделение логики бота, планировщика и настроек.
- Redis: интеграция для кэширования и хранения данных.
- Postgres: поддержка для работы с базой данных.
- Sqlalchemy: ORM для работы с базой данных.
- i18n: поддержка многоязычных сообщений.
- Systemd Unit-файлы: примеры для автозапуска бота и планировщика на Linux (Ubuntu).

## Требования

- Python 3.10 или выше
- Redis
- Ubuntu (для установки и настройки на сервере)

## Установка

### 1. Клонирование репозитория

```bash
git clone https://github.com/Solarmove/aiogram_bot_template.git
cd aiogram_bot_template
```

### 2. Настройка виртуального окружения

Рекомендуется использовать виртуальное окружение для изоляции зависимостей:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Установка зависимостей

Установите необходимые пакеты из файла requirements.txt:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Настройка переменных окружения

Скопируйте пример файла окружения и отредактируйте его в соответствии с вашими настройками:

```bash
cp .env.example .env
nano .env
```

Или Vim:

```bash
vim .env
```

Заполните необходимые данные (токен бота, настройки подключения к Redis и т.д.).

### 5. Запуск бота

#### Ручной запуск

Запустите бота командой:

```bash
python3 -m bot
```

Запуск планировщика

```bash
arq scheduler.main.WorkerSettings
```

#### Автоматический запуск с помощью systemd

В папке systemd находятся примеры unit-файлов для запуска бота и планировщика. Скопируйте файлы в
директорию `/etc/systemd/system/`:

```bash
sudo cp systemd/aiogram_bot.service /etc/systemd/system/
sudo cp systemd/aiogram_scheduler.service /etc/systemd/system/
```

Перезагрузите systemd и запустите сервисы:

```bash
sudo systemctl daemon-reload
sudo systemctl start aiogram_bot.service
sudo systemctl start aiogram_scheduler.service
```

Для автоматического запуска при загрузке системы выполните:

```bash
sudo systemctl enable aiogram_bot.service
sudo systemctl enable aiogram_scheduler.service
```

## Использование

- Добавление логики: Расширяйте функциональность бота, добавляя новые хэндлеры и команды в
  директории `bot/`.
- Планировщик: Используйте модуль `scheduler` для выполнения периодических
  задач. ([Документация](https://arq-docs.helpmanual.io/))
- Многоязычность: Добавляйте файлы переводов и используйте встроенную поддержку i18n для локализации
  сообщений.

## Вклад в проект

Если у вас есть идеи или улучшения:

1. Сделайте fork репозитория.
2. Создайте новую ветку для своей функциональности.
3. Отправьте pull request с описанием изменений.
