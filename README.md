# SalaryApp

![CI](https://github.com/diablotaurus/SalaryApp/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/github/license/diablotaurus/SalaryApp)
![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)

Учёт личной заработной платы: desktop-приложение, веб-интерфейс и Telegram-бот на едином ядре.
Помесячный учёт аванса и зарплаты, суммирование и аналитика по периодам.

*Personal salary tracker: a desktop app, a web interface and a Telegram bot sharing one core.
Tracks monthly advance and salary payments and provides per-period analytics.*

---

## 🇷🇺 Описание

**SalaryApp** ведёт учёт доходов помесячно: аванс, зарплата, даты выплат — и даёт сводки и графики.
Три интерфейса работают поверх общего ядра (`core`): модели, репозитории и сервисы переиспользуются
во всех частях. Архитектура следует принципам MVC, OOP, DRY и SOLID.

### Возможности
- 📅 Помесячный ввод аванса и зарплаты с датами выплат.
- 📊 Аналитика: помесячная динамика, сравнение по годам, темпы роста, средние по месяцам, лучшие периоды.
- 💾 Резервные копии БД (создание/восстановление, авто-бэкап при закрытии).
- 📤 Экспорт в CSV / JSON / Excel.
- 🖥️ Desktop (Tkinter), 🌐 Web (Flask), 🤖 Telegram-бот (aiogram).

### Компоненты
| Часть | Точка входа | Технологии |
|---|---|---|
| Desktop | `StartSalary.pyw` | Tkinter (MVC: views/controllers/presenters) |
| Web | `run_web.py` | Flask (blueprints, JSON API) |
| Telegram-бот | `run_bot.py` | aiogram v3 (FSM) |
| Общее ядро | `core/` | модели, репозитории, сервисы, SQLite, миграции |

### Структура проекта
```
core/      — модели, репозитории, сервисы, конфигурация, БД, утилиты (общее ядро)
api/       — фасад прикладного API (используется web и ботом)
desktop/   — desktop-приложение (MVC)
web/       — Flask-приложение (маршруты, шаблоны, статика)
bot/       — Telegram-бот
scripts/   — служебные скрипты (в т.ч. деплой, см. scripts/DEPLOY.md)
tests/     — модульные, интеграционные и smoke-тесты
docs/      — changelog'и (история версий)
```

### Установка
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### Запуск
```bash
# Desktop (без консоли)
python StartSalary.pyw      # или: python -m desktop

# Web
python run_web.py           # по умолчанию http://127.0.0.1:5000

# Telegram-бот
python run_bot.py
```

### Настройка Telegram-бота
1. Получите токен у [@BotFather](https://t.me/BotFather).
2. Скопируйте `bot/.env.example` в `bot/.env` и впишите токен:
   ```
   BOT_TOKEN=ваш_токен
   ```
   Токен также можно задать переменной окружения `SALARYAPP_BOT_TOKEN` или `BOT_TOKEN`.

### Тесты
```bash
python -m pytest
```

### Деплой
Ручной перенос в production описан в [`scripts/DEPLOY.md`](scripts/DEPLOY.md).

---

## 🇬🇧 Overview (English)

**SalaryApp** is a personal salary tracker with three front-ends (desktop, web, Telegram bot)
built on a shared core. It records monthly advance/salary payments and provides analytics
(monthly dynamics, year-over-year comparison, growth rate, monthly averages, best periods),
database backups and exports to CSV/JSON/Excel.

- **Stack:** Python, Tkinter, Flask, aiogram v3, SQLite, openpyxl, matplotlib.
- **Run:** `python StartSalary.pyw` (desktop), `python run_web.py` (web), `python run_bot.py` (bot).
- **Setup bot token:** copy `bot/.env.example` to `bot/.env` and set `BOT_TOKEN`.
- **Tests:** `python -m pytest`.

---

## 📄 Лицензия / License

Apache License 2.0 — см. файл [`LICENSE`](LICENSE).

© 2026 diablotaurus
