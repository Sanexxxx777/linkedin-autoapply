"""Конфиг LinkedIn semi-auto бота.
Бот НЕ подаёт заявки сам (LinkedIn SDUI Easy Apply блокирует автоматизацию —
форма в shadow DOM не наполняется). Режим: scan + LLM-скоринг + карточка в TG,
Саша подаёт сам по ссылке.

Ищем ВСЕ релевантные вакансии (не только Easy Apply): scan без f_AL,
бейдж Easy Apply детектится отдельно. Карточка показывает способ подачи.
"""

# Поисковые запросы LinkedIn (scan без f_AL — и Easy Apply, и внешняя форма)
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

# LLM делит источник на 3 типа (agency_type): direct (сам работодатель),
# staffing (классическое агентство-посредник, ghost jobs/сбор CV), talent_network
# (Proxify/Toptal/Turing — рабочий канал удалёнки, НЕ штрафуем, метим 🌐).
# Политика применяется к ЛЮБОМУ staffing (и Easy Apply, и внешним) — оставляем
# только надёжные агентства (talent_network) + прямых работодателей:
# "drop" — staffing не слать вовсе (только хорошие/надёжные).
# "flag" — слать с пометкой ⚠️, но требовать повышенный порог AGENCY_SCORE_THRESHOLD.
AGENCY_POLICY = "drop"
AGENCY_SCORE_THRESHOLD = 80

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

# LLM модель для скоринга. Gemini primary (умнее), ключ обновлён 22.06 (рабочий).
# При 429 (free 15 RPM на пакете 20 вак) ask_llm уходит в fallback-цепочку, где
# Groq стоит ПЕРВЫМ (claude_client._build_fallback_chain) → быстрый подхват без
# повторного удара в Gemini. Переключить на Groq основным: SCORING_MODEL="llama-3.3-70b-versatile".
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
