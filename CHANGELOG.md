# Changelog

Все значимые изменения проекта документируются здесь.
Формат — по [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/), версии — [SemVer](https://semver.org/lang/ru/).

## [1.0.0] — 2026-06-09

Первая версионированная сборка.

### Added
- Очистка `seen_jobs.json` от записей старше 30 дней (`cleanup_seen`).
- Ежедневная сводка в Telegram (`maybe_daily_summary`): просмотрено/отправлено за сутки.
- Watchdog при зависании цикла шлёт уведомление в Telegram.
- Критические ошибки цикла отправляются в Telegram.

### Changed
- Бот отвязан от `hh-autoapply`: собственный `.env` и локальная копия `claude_client.py`
  вместо `sys.path.insert` в чужую папку.
- Алерт о протухшей сессии throttle'ится (не чаще раза в 3 часа) — больше не спамит.
- VNC-пароль вынесен из кода в `.env` (`VNC_PASSWORD`).

### Security
- `.gitignore` исключает `.env`, `auth_state.json`, `data/` из репозитория.
