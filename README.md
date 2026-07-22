# linkedin-autoapply

<!-- TODO: demo GIF (20-40s) — record with screen capture, see /Users/sasha/.claude memory reference_browser_automation_demo_reel or ghostty recorder -->

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

## Пример результата

<!-- TODO: реальный пример вывода (скриншот TG-карточки или лог-сэмпл) — не выдумывать, добавить когда будет -->

## ⚠️ Риски

- Браузерная автоматизация LinkedIn (даже read-only скан без автоподачи) может нарушать
  условия использования платформы. Обнаруженная автоматизация может привести к временной
  или постоянной блокировке аккаунта.
- Используйте умеренные лимиты (`CHECK_INTERVAL_MINUTES`, паузы между запросами), не
  запускайте несколько сканов на один аккаунт параллельно.
- Используете на свой риск — перед запуском ознакомьтесь с актуальными условиями LinkedIn.

## License

[MIT](LICENSE)

## Автор

Aleksandr Shulgin ([@Sanexxxx777](https://github.com/Sanexxxx777)) (@Aleksandr_NFA)

---

## English summary

Semi-automatic LinkedIn job scanner: searches Easy Apply vacancies by keyword queries, scores
relevance with an LLM (Gemini → Groq fallback), and sends matching cards to Telegram. It does
**not** submit applications itself (LinkedIn's Easy Apply form lives in a shadow DOM that blocks
automation) — the candidate applies via a link in two clicks. Complements
[hh-autoapply](https://github.com/Sanexxxx777/hh-autoapply) for a market where full auto-apply
isn't available. Stack: Python 3 + Playwright, Telegram Bot API, pm2. See `## Запуск` above for
setup (English variable names, same commands).

⚠️ Browser automation against LinkedIn can violate its Terms of Service and risk an account
ban — use at your own risk with conservative rate limits.
