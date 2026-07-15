# linkedin-autoapply

Полуавтоматический сканер вакансий LinkedIn: ищет Easy Apply вакансии по ключевым
запросам, оценивает релевантность через LLM и присылает карточки подходящих в Telegram.
Заявки **не подаёт сам** (форма LinkedIn Easy Apply в shadow DOM блокирует автоматизацию) —
кандидат подаёт по ссылке в 2 клика.

Дополняет [hh-autoapply](https://github.com/Sanexxxx777/hh-autoapply) для рынка,
где автоотклик недоступен: LinkedIn активно блокирует автоматизацию формы подачи,
поэтому бот берёт на себя только скан и LLM-скоринг, оставляя финальный клик человеку.

## Стек

- Python 3 + Playwright (браузерный скан вакансий LinkedIn)
- LLM-роутер с fallback-цепочкой: Gemini → Groq
- Telegram Bot API — карточки вакансий и ежедневная сводка
- pm2 — процесс-менеджер для цикличного запуска

## Запуск

```bash
pip install playwright python-dotenv requests
playwright install chromium
cp .env.example .env   # заполнить ключи и токены
python3 main.py --once     # один цикл
python3 main.py --loop     # цикл каждые CHECK_INTERVAL_MINUTES (для pm2)
DRY_RUN=1 python3 main.py --once   # печать карточек вместо отправки в TG
```

## Конфигурация

- `config.py` — ключевые запросы, порог скоринга, рабочее окно, профиль кандидата
  для LLM-скоринга (правится под себя).
- `.env` — секреты (см. `.env.example`).

## Архитектура

- `main.py` — цикл: scan → дедуп → LLM-скоринг → карточка в TG.
- `claude_client.py` — LLM-роутер (Gemini/Groq fallback).
- `scrape_profile.py` / `scrape_v2.py` — сбор профиля.
- `dev/` — отладочные скрипты (не используются в проде).

## Автор

Aleksandr Shulgin ([@Sanexxxx777](https://github.com/Sanexxxx777))
