"""Диагностика рендера страницы вакансии LinkedIn (почему нет apply-кнопки)."""
from playwright.sync_api import sync_playwright
import json, time

STATE = '/root/linkedin-autoapply/auth_state.json'
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
with open('/root/linkedin-autoapply/data/jobs_scan.json') as f:
    job = json.load(f)[0]

pw = sync_playwright().start()
b = pw.chromium.launch(headless=True, args=[
    '--no-sandbox', '--disable-blink-features=AutomationControlled',
    '--disable-dev-shm-usage', '--disable-gpu', '--js-flags=--max-old-space-size=512',
])
ctx = b.new_context(storage_state=STATE, user_agent=UA, locale='en-US',
                    viewport={'width': 1366, 'height': 900})
ctx.route('**/*', lambda r: r.abort()
          if r.request.resource_type in ('media', 'font') else r.continue_())
page = ctx.new_page()
page.set_default_timeout(25000)

print(f'goto: {job["url"]}', flush=True)
page.goto(job['url'], wait_until='domcontentloaded')
time.sleep(8)
try:
    page.wait_for_selector('.job-details-jobs-unified-top-card__container, .jobs-unified-top-card, h1', timeout=15000)
    print('top-card дождались', flush=True)
except Exception as e:
    print(f'top-card НЕ появился: {e}', flush=True)
# скролл к деталям
for _ in range(3):
    page.mouse.wheel(0, 800); time.sleep(1)

print(f'title: {page.title()}', flush=True)
print(f'url:   {page.url}', flush=True)
allbtn = page.query_selector_all('button')
print(f'\nвсего <button>: {len(allbtn)}', flush=True)
shown = 0
for bel in allbtn:
    try:
        vis = bel.is_visible()
        t = (bel.inner_text() or '').strip()
        a = bel.get_attribute('aria-label') or ''
        if (t or a) and shown < 40:
            print(f'  vis={vis} text="{t[:40]}" aria="{a[:50]}"', flush=True)
            shown += 1
    except Exception:
        pass

# ключевые контейнеры
print('\n--- контейнеры ---', flush=True)
for sel in ['.jobs-apply-button', '.jobs-s-apply', '.job-details-jobs-unified-top-card__container',
            '.jobs-unified-top-card', 'div.jobs-details', 'main', '.scaffold-layout__detail',
            'a[href*="/apply/"]', '[class*="apply"]']:
    els = page.query_selector_all(sel)
    print(f'  {sel}: {len(els)}', flush=True)

# дамп текста main-области (первые 600 симв)
main = page.query_selector('main')
if main:
    print(f'\n--- main text (600) ---\n{(main.inner_text() or "")[:600]}', flush=True)

page.screenshot(path='/root/linkedin-autoapply/data/job_debug.png')
print('\nскриншот: data/job_debug.png', flush=True)
b.close(); pw.stop()
