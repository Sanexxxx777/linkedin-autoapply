"""Прицельный дамп apply-элемента LinkedIn (тег/текст/видимость/HTML)."""
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
page.goto(job['url'], wait_until='domcontentloaded')
time.sleep(9)

# 1. apply-ссылки
print('=== a[href*="/apply/"] ===', flush=True)
for el in page.query_selector_all('a[href*="/apply/"]'):
    print(f'  text="{(el.inner_text() or "").strip()[:60]}" vis={el.is_visible()} href={(el.get_attribute("href") or "")[:70]}', flush=True)
    print(f'  HTML: {el.evaluate("e=>e.outerHTML")[:300]}', flush=True)

# 2. любой элемент с текстом "подача заявки" (кнопка/ссылка/div)
print('\n=== элементы с "подач" (button,a,div[role=button]) ===', flush=True)
for el in page.query_selector_all('button, a, div[role="button"], span'):
    try:
        t = (el.inner_text() or '').strip()
        if 'подач' in t.lower() and len(t) < 40 and el.is_visible():
            tag = el.evaluate('e=>e.tagName.toLowerCase()')
            print(f'  <{tag}> "{t}" cls={(el.get_attribute("class") or "")[:50]}', flush=True)
    except Exception:
        pass

# 3. top-card новые классы — что вообще есть
print('\n=== классы верхней карточки (sample) ===', flush=True)
for sel in ['[class*="top-card"]', '[class*="apply"]', '[class*="jobs-apply"]',
            'div.jobs-s-apply', '[componentkey]', '.artdeco-button--primary']:
    els = page.query_selector_all(sel)
    print(f'  {sel}: {len(els)}', flush=True)
    if els and len(els) <= 5:
        for e in els[:5]:
            try:
                print(f'      "{(e.inner_text() or "").strip()[:40]}" vis={e.is_visible()}', flush=True)
            except Exception:
                pass

b.close(); pw.stop()
