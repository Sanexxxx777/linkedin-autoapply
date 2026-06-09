"""Надёжный парсинг Easy Apply вакансий LinkedIn (read-only).
Фикс памяти: без full_page, блок шрифтов/медиа, один список."""
from playwright.sync_api import sync_playwright
import json, time, random, sys

STATE = '/root/linkedin-autoapply/auth_state.json'
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
KW = sys.argv[1] if len(sys.argv) > 1 else 'python developer'

def human(a=1.5, b=3.5):
    time.sleep(random.uniform(a, b))

pw = sync_playwright().start()
b = pw.chromium.launch(headless=True, args=[
    '--no-sandbox', '--disable-blink-features=AutomationControlled',
    '--disable-dev-shm-usage', '--disable-gpu', '--js-flags=--max-old-space-size=512',
])
ctx = b.new_context(storage_state=STATE, user_agent=UA, locale='en-US',
                    viewport={'width': 1366, 'height': 900})
# экономия памяти: не грузим шрифты/медиа
ctx.route('**/*', lambda r: r.abort()
          if r.request.resource_type in ('media', 'font') else r.continue_())
page = ctx.new_page()

url = ('https://www.linkedin.com/jobs/search/?f_AL=true&keywords='
       + KW.replace(' ', '%20') + '&sortBy=DD')
print(f'[scan] keywords="{KW}"\n[scan] {url}', flush=True)
page.goto(url, wait_until='domcontentloaded')
human(4, 7)

# скролл списка для подгрузки карточек
for _ in range(5):
    page.mouse.wheel(0, 1200)
    human(1, 2)

SEL_CARD = ['div.job-card-container', 'li.scaffold-layout__list-item',
            'div[data-job-id]', 'li.jobs-search-results__list-item']
cards = []
for s in SEL_CARD:
    cards = page.query_selector_all(s)
    if cards:
        print(f'[scan] селектор сработал: {s} → {len(cards)} карточек', flush=True)
        break

jobs = []
for c in cards[:25]:
    try:
        jid = c.get_attribute('data-job-id') or ''
        link_el = c.query_selector('a[href*="/jobs/view/"], a.job-card-container__link, a.job-card-list__title--link')
        href = link_el.get_attribute('href') if link_el else ''
        title = ''
        for ts in ['a.job-card-list__title--link', '.job-card-list__title', 'a[class*=title]', 'strong']:
            te = c.query_selector(ts)
            if te and (te.inner_text() or '').strip():
                title = te.inner_text().strip().split('\n')[0]
                break
        comp = ''
        for cs in ['.artdeco-entity-lockup__subtitle', '.job-card-container__primary-description',
                   'span.job-card-container__company-name', '.job-card-list__company-name']:
            ce = c.query_selector(cs)
            if ce and (ce.inner_text() or '').strip():
                comp = ce.inner_text().strip()
                break
        if title or jid:
            jobs.append({'job_id': jid, 'title': title, 'company': comp,
                         'url': ('https://www.linkedin.com' + href.split('?')[0]) if href.startswith('/') else href})
    except Exception as e:
        print(f'[scan] карточка err: {e}', flush=True)

print(f'[scan] распарсено вакансий: {len(jobs)}', flush=True)
for j in jobs[:10]:
    print(f"  • {j['title']} — {j['company']} [{j['job_id']}]", flush=True)

with open('/root/linkedin-autoapply/data/jobs_scan.json', 'w') as f:
    json.dump(jobs, f, ensure_ascii=False, indent=2)
print('[scan] сохранено в data/jobs_scan.json', flush=True)
b.close(); pw.stop()
print('[scan] готово', flush=True)
