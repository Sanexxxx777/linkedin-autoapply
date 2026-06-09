"""LinkedIn semi-auto бот: scan Easy Apply вакансий → LLM-скоринг → карточка в TG.
НЕ подаёт заявки сам (LinkedIn SDUI блокирует автоматизацию формы). Саша подаёт по ссылке.

Запуск:
  python3 main.py --once          один цикл
  python3 main.py --loop          цикл каждые CHECK_INTERVAL_MINUTES (для pm2)
  DRY_RUN=1 python3 main.py --once   печать карточек вместо отправки в TG
"""
import os, sys, json, time, random, argparse, threading, traceback, re
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv
_HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_HERE, '.env'))

# самодостаточный LLM-роутер (локальная копия, без привязки к hh-autoapply)
sys.path.insert(0, _HERE)
from claude_client import ask_llm  # noqa: E402
import config  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

STATE = '/root/linkedin-autoapply/auth_state.json'
SEEN_FILE = '/root/linkedin-autoapply/data/seen_jobs.json'
SESSION_ALERT_FLAG = '/root/linkedin-autoapply/.last_session_alert'
SEEN_TTL_DAYS = 30
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
TG_TOKEN = os.getenv('TG_BOT_TOKEN')
TG_CHAT = os.getenv('TG_CHAT_ID')
DRY_RUN = os.getenv('DRY_RUN') == '1'

import requests  # noqa: E402


def human(a=1.5, b=3.5):
    time.sleep(random.uniform(a, b))


# ---------- дедуп ----------
def load_seen() -> dict:
    try:
        with open(SEEN_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_seen(seen: dict):
    os.makedirs(os.path.dirname(SEEN_FILE), exist_ok=True)
    tmp = SEEN_FILE + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)
    os.replace(tmp, SEEN_FILE)


def cleanup_seen(seen: dict) -> dict:
    """Убираем записи старше SEEN_TTL_DAYS — иначе seen_jobs.json растёт без предела."""
    cutoff = time.time() - SEEN_TTL_DAYS * 86400
    cleaned = {k: v for k, v in seen.items() if v.get('ts', 0) >= cutoff}
    if len(cleaned) < len(seen):
        print(f'  🧹 seen cleanup: {len(seen)} → {len(cleaned)}', flush=True)
    return cleaned


SUMMARY_FLAG = '/root/linkedin-autoapply/.last_summary_date'


def maybe_daily_summary(seen: dict):
    """Раз в день (DAILY_SUMMARY_HOUR_MSK) — сводка за последние сутки в TG."""
    msk = datetime.now(timezone(timedelta(hours=3)))
    if msk.hour != getattr(config, 'DAILY_SUMMARY_HOUR_MSK', 21):
        return
    today = msk.strftime('%Y-%m-%d')
    try:
        with open(SUMMARY_FLAG) as f:
            if f.read().strip() == today:
                return
    except Exception:
        pass
    day_ago = time.time() - 86400
    recent = [v for v in seen.values() if v.get('ts', 0) >= day_ago]
    sent = [v for v in recent if v.get('sent')]
    text = (f'📊 <b>[LinkedIn] сводка за день</b>\n\n'
            f'Просмотрено вакансий: <b>{len(recent)}</b>\n'
            f'Подходящих (отправлено): <b>{len(sent)}</b>')
    tg_send(text)
    try:
        with open(SUMMARY_FLAG, 'w') as f:
            f.write(today)
    except Exception:
        pass


# ---------- TG ----------
def tg_send(text: str, url: str = ''):
    if DRY_RUN:
        print(f'\n[DRY TG]\n{text}\n  url={url}', flush=True)
        return
    payload = {'chat_id': TG_CHAT, 'text': text, 'parse_mode': 'HTML',
               'disable_web_page_preview': True}
    if url:
        payload['reply_markup'] = {'inline_keyboard': [[
            {'text': '↗ Открыть вакансию', 'url': url}]]}
    try:
        r = requests.post(f'https://api.telegram.org/bot{TG_TOKEN}/sendMessage',
                          json=payload, timeout=15)
        if not r.json().get('ok'):
            print(f'  ⚠️ TG error: {r.text[:200]}', flush=True)
    except Exception as e:
        print(f'  ⚠️ TG send failed: {e}', flush=True)


# ---------- LLM скоринг ----------
def score_job(title: str, company: str, description: str) -> dict:
    prompt = f"""Ты — ассистент по подбору вакансий. Оцени релевантность вакансии профилю кандидата.

ПРОФИЛЬ КАНДИДАТА:
{config.PROFILE}

ВАКАНСИЯ:
Название: {title}
Компания: {company}
Описание: {description[:3000]}

Верни СТРОГО JSON без markdown:
{{"score": <0-100 целое, насколько вакансия подходит>, "reason": "<1 короткая фраза по-русски почему>"}}"""
    try:
        raw = ask_llm(prompt, model=config.SCORING_MODEL, max_tokens=300)
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if not m:
            return {'score': 0, 'reason': 'LLM не вернул JSON'}
        data = json.loads(m.group(0))
        return {'score': int(data.get('score', 0)), 'reason': str(data.get('reason', ''))[:200]}
    except Exception as e:
        return {'score': 0, 'reason': f'scoring err: {e}'}


# ---------- браузер ----------
class LIBrowser:
    def __init__(self):
        self._pw = None
        self._b = None
        self._ctx = None
        self.page = None

    def start(self):
        self._pw = sync_playwright().start()
        self._b = self._pw.chromium.launch(headless=True, args=[
            '--no-sandbox', '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage', '--disable-gpu', '--disable-extensions',
            '--disable-background-networking', '--js-flags=--max-old-space-size=512',
        ])
        self._ctx = self._b.new_context(storage_state=STATE, user_agent=UA,
                                        locale='en-US', viewport={'width': 1366, 'height': 900})
        self._ctx.route('**/*', lambda r: r.abort()
                        if r.request.resource_type in ('media', 'font') else r.continue_())
        self.page = self._ctx.new_page()
        self.page.set_default_timeout(25000)

    def close(self):
        for fn in (lambda: self._ctx and self._ctx.close(),
                   lambda: self._b and self._b.close(),
                   lambda: self._pw and self._pw.stop()):
            try:
                fn()
            except Exception:
                pass

    def is_logged_in(self) -> bool:
        self.page.goto('https://www.linkedin.com/feed/', wait_until='domcontentloaded')
        human(3, 5)
        cur = self.page.url
        return not any(x in cur for x in ('/login', '/checkpoint', '/authwall', '/uas/login'))

    def scan(self, keyword: str) -> list:
        url = ('https://www.linkedin.com/jobs/search/?f_AL=true&keywords='
               + keyword.replace(' ', '%20') + '&sortBy=DD')
        try:
            self.page.goto(url, wait_until='domcontentloaded')
        except Exception as e:
            print(f'  scan goto err: {e}', flush=True)
            return []
        human(4, 6)
        for _ in range(5):
            self.page.mouse.wheel(0, 1200)
            human(1, 2)
        cards = []
        for s in ['div.job-card-container', 'li.scaffold-layout__list-item', 'div[data-job-id]']:
            cards = self.page.query_selector_all(s)
            if cards:
                break
        jobs = []
        for c in cards[:25]:
            try:
                jid = c.get_attribute('data-job-id') or ''
                link = c.query_selector('a[href*="/jobs/view/"]')
                href = link.get_attribute('href') if link else ''
                title = ''
                for ts in ['a.job-card-list__title--link', '.job-card-list__title', 'a[class*=title]', 'strong']:
                    te = c.query_selector(ts)
                    if te and (te.inner_text() or '').strip():
                        title = te.inner_text().strip().split('\n')[0]
                        break
                comp = ''
                for cs in ['.artdeco-entity-lockup__subtitle', '.job-card-container__primary-description',
                           'span.job-card-container__company-name']:
                    ce = c.query_selector(cs)
                    if ce and (ce.inner_text() or '').strip():
                        comp = ce.inner_text().strip()
                        break
                if (title or jid) and href:
                    jobs.append({'job_id': jid, 'title': title, 'company': comp,
                                 'url': ('https://www.linkedin.com' + href.split('?')[0])
                                 if href.startswith('/') else href.split('?')[0]})
            except Exception:
                pass
        return jobs

    def get_description(self, job_url: str) -> str:
        try:
            self.page.goto(job_url, wait_until='domcontentloaded')
        except Exception:
            return ''
        time.sleep(6)
        # описание грузится lazy при скролле вниз
        for _ in range(4):
            self.page.mouse.wheel(0, 1000)
            human(0.8, 1.5)
        # раскрыть «… развернуть» если есть
        try:
            more = self.page.query_selector('button:has-text("развернуть"), button:has-text("see more"), button:has-text("Показать ещё")')
            if more and more.is_visible():
                more.click()
                human(1, 2)
        except Exception:
            pass
        main = self.page.query_selector('main')
        return (main.inner_text() if main else '')[:3500]


# ---------- watchdog (урок HH: отменяемый) ----------
def _watchdog(timeout, done_event):
    if done_event.wait(timeout):
        return
    print(f'\n🔥 WATCHDOG: цикл завис >{timeout // 60} мин — выход', flush=True)
    sys.stdout.flush()
    try:
        tg_send(f'🔥 <b>[LinkedIn]</b> watchdog: цикл завис >{timeout // 60} мин, перезапуск')
    except Exception:
        pass
    os._exit(1)


# ---------- цикл ----------
def run_once():
    wh = config.WORK_HOURS_MSK
    hour_msk = datetime.now(timezone(timedelta(hours=3))).hour
    if os.getenv('LI_FORCE') != '1' and not (wh[0] <= hour_msk < wh[1]):
        print(f'💤 {hour_msk}:00 МСК вне диапазона {wh[0]}-{wh[1]} — skip', flush=True)
        return

    done = threading.Event()
    threading.Thread(target=_watchdog, args=(config.CYCLE_TIMEOUT, done), daemon=True).start()

    print(f'🚀 LinkedIn semi-auto — {datetime.now().strftime("%Y-%m-%d %H:%M")}'
          f'{" [DRY]" if DRY_RUN else ""}', flush=True)
    seen = cleanup_seen(load_seen())
    br = LIBrowser()
    br.start()
    new_count = 0
    try:
        if not br.is_logged_in():
            vnc_pass = os.getenv('VNC_PASSWORD', '—')
            msg = ('🚨 <b>[LinkedIn] сессия протухла</b>\n\n'
                   'Нужен релогин через VNC:\n'
                   f'<code>vnc://45.82.95.134:5903</code> (пароль <code>{vnc_pass}</code>)\n'
                   'Открой Chromium, залогинься. Затем: <code>python3 do_login.py</code>')
            # throttle: не спамим алертом о сессии чаще раза в 3 часа
            now = time.time()
            last = 0.0
            try:
                with open(SESSION_ALERT_FLAG) as f:
                    last = float(f.read().strip())
            except Exception:
                pass
            if now - last >= 3 * 3600:
                tg_send(msg)
                try:
                    with open(SESSION_ALERT_FLAG, 'w') as f:
                        f.write(str(now))
                except Exception:
                    pass
            print('⚠️ сессия мертва', flush=True)
            return
        print('✅ сессия активна', flush=True)

        # 1. собрать вакансии по всем keyword
        found = {}
        for kw in config.KEYWORDS:
            jobs = br.scan(kw)
            print(f'  [{kw}] → {len(jobs)} вакансий', flush=True)
            for j in jobs:
                if j['job_id'] and j['job_id'] not in found:
                    found[j['job_id']] = j
            human(2, 4)

        # 2. отфильтровать новые
        fresh = [j for jid, j in found.items() if jid not in seen]
        print(f'  всего уникальных: {len(found)}, новых: {len(fresh)}', flush=True)
        fresh = fresh[:config.MAX_PER_CYCLE]

        # 3. скоринг + карточка
        for j in fresh:
            desc = br.get_description(j['url'])
            sc = score_job(j['title'], j['company'], desc)
            print(f"  • [{sc['score']}] {j['title']} — {j['company']}: {sc['reason']}", flush=True)
            seen[j['job_id']] = {'ts': int(time.time()), 'title': j['title'],
                                 'company': j['company'], 'score': sc['score'], 'sent': False}
            if sc['score'] >= config.SCORE_THRESHOLD:
                card = (f"🔗 <b>[LinkedIn]</b> подходящая вакансия\n\n"
                        f"<b>{j['title']}</b>\n"
                        f"🏢 {j['company']}\n"
                        f"🎯 Релевантность: <b>{sc['score']}/100</b>\n"
                        f"💬 {sc['reason']}\n\n"
                        f"<i>Easy Apply — подай сам в 2 клика по кнопке ниже.</i>")
                tg_send(card, url=j['url'])
                seen[j['job_id']]['sent'] = True
                new_count += 1
            save_seen(seen)
            human(2, 5)

        save_seen(seen)
        maybe_daily_summary(seen)
        print(f'\n✅ Цикл завершён: отправлено карточек {new_count}', flush=True)
    except Exception as e:
        print(f'\n❌ Ошибка: {e}', flush=True)
        traceback.print_exc()
    finally:
        br.close()
        done.set()


def run_loop():
    interval = config.CHECK_INTERVAL_MINUTES
    print(f'🔄 LinkedIn semi-auto loop: каждые {interval} мин', flush=True)
    while True:
        try:
            run_once()
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f'❌ критическая: {e}', flush=True)
            traceback.print_exc()
            try:
                tg_send(f'⚠️ <b>[LinkedIn] критическая ошибка:</b>\n<code>{str(e)[:500]}</code>')
            except Exception:
                pass
        print(f'💤 след. запуск через {interval} мин', flush=True)
        time.sleep(interval * 60)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--once', action='store_true')
    ap.add_argument('--loop', action='store_true')
    args = ap.parse_args()
    if args.loop:
        run_loop()
    else:
        run_once()
