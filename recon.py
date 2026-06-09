"""LinkedIn мягкая разведка (read-only, БЕЗ отправки откликов).
Читает профиль, парсит Easy Apply вакансии, заглядывает в 1 форму.
Человеческие задержки, стелс-настройки против анти-бот систем."""
from playwright.sync_api import sync_playwright
import json, time, random, os

STATE = '/root/linkedin-autoapply/auth_state.json'
DATA = '/root/linkedin-autoapply/data'
os.makedirs(DATA, exist_ok=True)
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')

def human(a=2.0, b=5.0):
    time.sleep(random.uniform(a, b))

STEALTH = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
window.chrome = {runtime: {}};
"""

def first_text(page, selectors):
    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el:
                t = (el.inner_text() or '').strip()
                if t:
                    return t
        except Exception:
            pass
    return ''

pw = sync_playwright().start()
b = pw.chromium.launch(headless=True, args=[
    '--no-sandbox', '--disable-blink-features=AutomationControlled',
    '--disable-dev-shm-usage',
])
ctx = b.new_context(
    storage_state=STATE, user_agent=UA, locale='en-US',
    viewport={'width': 1366, 'height': 800},
    timezone_id='Europe/Amsterdam',
)
ctx.add_init_script(STEALTH)
page = ctx.new_page()

report = {'profile': {}, 'jobs': [], 'apply_form': {}, 'errors': []}

# --- ФАЗА 1: профиль ---
try:
    print('[recon] открываю свой профиль...', flush=True)
    page.goto('https://www.linkedin.com/in/me/', wait_until='domcontentloaded')
    human(3, 6)
    page.screenshot(path='/tmp/li_profile.png', full_page=False)
    name = first_text(page, ['h1', 'h1.text-heading-xlarge', '.pv-text-details__left-panel h1'])
    headline = first_text(page, ['.text-body-medium.break-words',
                                 '.pv-text-details__left-panel .text-body-medium',
                                 'div.text-body-medium'])
    location = first_text(page, ['.text-body-small.inline.t-black--light.break-words',
                                 'span.text-body-small.inline'])
    report['profile'] = {'name': name, 'headline': headline,
                         'location': location, 'url': page.url}
    print(f'[recon] профиль: {name} | {headline} | {location}', flush=True)
except Exception as e:
    report['errors'].append(f'profile: {e}')
    print(f'[recon] ошибка профиля: {e}', flush=True)

# ключевые слова поиска из headline
kw = (report['profile'].get('headline') or 'developer').split('|')[0].split('·')[0].strip()[:40]
human()

# --- ФАЗА 2: поиск Easy Apply вакансий ---
try:
    print(f'[recon] ищу Easy Apply вакансии по: "{kw}"...', flush=True)
    url = ('https://www.linkedin.com/jobs/search/?f_AL=true&keywords='
           + kw.replace(' ', '%20'))
    page.goto(url, wait_until='domcontentloaded')
    human(4, 7)
    page.screenshot(path='/tmp/li_jobs.png', full_page=False)
    cards = page.query_selector_all('.job-card-container, li.scaffold-layout__list-item, div.job-card-list')
    print(f'[recon] найдено карточек на странице: {len(cards)}', flush=True)
    for c in cards[:6]:
        try:
            report['jobs'].append({'raw': (c.inner_text() or '').strip()[:200]})
        except Exception:
            pass
except Exception as e:
    report['errors'].append(f'jobs: {e}')
    print(f'[recon] ошибка поиска: {e}', flush=True)

# --- ФАЗА 3: заглянуть в 1 форму Easy Apply (БЕЗ submit) ---
try:
    print('[recon] открываю первую вакансию для осмотра формы...', flush=True)
    link = page.query_selector('a.job-card-list__title, a.job-card-container__link, a[href*="/jobs/view/"]')
    if link:
        link.click()
        human(3, 6)
        btn = page.query_selector('button.jobs-apply-button, button[aria-label*="Easy Apply"], button[class*="jobs-apply"]')
        if btn:
            print('[recon] кнопка Easy Apply найдена, открываю модалку (БЕЗ отправки)...', flush=True)
            btn.click()
            human(3, 5)
            page.screenshot(path='/tmp/li_apply_form.png', full_page=False)
            modal = page.query_selector('.jobs-easy-apply-modal, div[role="dialog"]')
            report['apply_form'] = {
                'opened': True,
                'text': (modal.inner_text()[:800] if modal else ''),
            }
            # закрыть модалку БЕЗ отправки
            human()
            close = page.query_selector('button[aria-label*="Dismiss"], button[aria-label*="Close"]')
            if close:
                close.click()
                human(1, 2)
                discard = page.query_selector('button[data-control-name="discard_application_confirm_btn"], button[aria-label*="Discard"]')
                if discard:
                    discard.click()
            print('[recon] модалка закрыта без отправки', flush=True)
        else:
            report['apply_form'] = {'opened': False, 'note': 'Easy Apply кнопка не найдена'}
            print('[recon] Easy Apply кнопка не найдена на этой вакансии', flush=True)
except Exception as e:
    report['errors'].append(f'apply_form: {e}')
    print(f'[recon] ошибка формы: {e}', flush=True)

with open(f'{DATA}/recon_report.json', 'w') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(f'[recon] отчёт сохранён в {DATA}/recon_report.json', flush=True)
human()
b.close(); pw.stop()
print('[recon] готово', flush=True)
