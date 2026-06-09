"""Конфиг LinkedIn semi-auto бота.
Бот НЕ подаёт заявки сам (LinkedIn SDUI Easy Apply блокирует автоматизацию —
форма в shadow DOM не наполняется). Режим: scan + LLM-скоринг + карточка в TG,
Саша подаёт сам по ссылке в 2 клика.
"""

# Поисковые запросы LinkedIn (f_AL=true — только Easy Apply)
KEYWORDS = [
    # backend / core
    "python developer remote",
    "backend engineer python remote",
    "rust developer remote",
    # AI / LLM
    "ai engineer remote",
    "llm engineer remote",
    "machine learning engineer remote",
    "ai agent developer remote",
    "prompt engineer remote",
    # боты / автоматизация
    "automation engineer python remote",
    "telegram bot developer remote",
    # продукты / стартапы (вайбкодинг-культура: Claude Code / Cursor)
    "founding engineer remote",
    "full stack engineer python remote",
    # ресёрч / аналитика / quant
    "quantitative developer remote",
    "data analyst python remote",
    "research engineer ai remote",
]

# LLM-скоринг: слать карточку только если score >= порога
SCORE_THRESHOLD = 65

# Сколько новых вакансий максимум обрабатывать за один цикл (защита от API-флуда)
MAX_PER_CYCLE = 20

# Рабочее окно МСК (как у HH) — бот активен только в этом диапазоне
WORK_HOURS_MSK = (9, 22)

# Час МСК для ежедневной сводки в TG
DAILY_SUMMARY_HOUR_MSK = 21

# Период цикла (минуты) — pm2 --loop
CHECK_INTERVAL_MINUTES = 90

# Макс время одного цикла (сек) до принудительного выхода
CYCLE_TIMEOUT = 1200

# LLM модель для скоринга (дёшево + json mode)
SCORING_MODEL = "gemini-2.5-flash"

# Профиль кандидата для скоринга релевантности (Саша правит под себя)
PROFILE = """\
Кандидат: AI-augmented Python/Rust разработчик. Ежедневный стек — Claude Code, Cursor,
Composer (агентная разработка как основной инструмент). 5+ лет в crypto/quant.

Сильные стороны и подходящие направления:
- AI/LLM engineering: интеграция Claude/Gemini/OpenAI, tool-use, agent orchestration,
  MCP-серверы, prompt engineering, RAG/embeddings.
- Backend: async Python, FastAPI, WebSocket/REST, PostgreSQL, real-time pipelines.
- Rust для hot-path (EIP-712 signing, low-latency executors).
- Боты и автоматизация: Telegram (aiogram 3.x), Playwright browser-automation, scrapers.
- Разработка продуктов: full-stack (Vite+React дашборды), MVP, founding-engineer роли
  в стартапах с AI-first / vibe-coding культурой.
- Ресёрч и аналитика: backtesting, genetic optimization (NSGA-II), on-chain analytics,
  market microstructure, data analysis (Pandas/DuckDB).
- Crypto/Web3: биржевые API, prediction markets (Polymarket CLOB), DeFi, on-chain data.

Формат: REMOTE (обязательно), part-time или full-time, соло или малые команды.
English working proficiency, GMT+10 (Asia/EU overlap).

НЕ подходит: чистый frontend без backend/AI, sales/менеджмент/маркетинг, on-site без
удалёнки, вакансии без английского описания, поддержка legacy без новой разработки.
"""
