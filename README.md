# linkedin-autoapply

Полуавтоматический сканер вакансий LinkedIn: ищет Easy Apply вакансии по ключевым
запросам, оценивает релевантность через LLM и присылает карточки подходящих в Telegram.
Заявки **не подаёт сам** (форма LinkedIn Easy Apply в shadow DOM блокирует автоматизацию) —
кандидат подаёт по ссылке в 2 клика.

## Запуск

```bash
python3 main.py --once     # один цикл
python3 main.py --loop     # цикл каждые CHECK_INTERVAL_MINUTES (для pm2)
DRY_RUN=1 python3 main.py --once   # печать карточек вместо отправки в TG
```

## Конфигурация

- `config.py` — ключевые запросы, порог скоринга, рабочее окно, профиль кандидата.
- `.env` — секреты (см. `.env.example`).

## Архитектура

- `main.py` — цикл: scan → дедуп → LLM-скоринг → карточка в TG.
- `claude_client.py` — LLM-роутер (Gemini/Groq fallback).
- `scrape_profile.py` / `scrape_v2.py` — сбор профиля.
- `dev/` — отладочные скрипты (не используются в проде).
