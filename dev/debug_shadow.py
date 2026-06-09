"""Проверка: SDUI Easy Apply форма в Shadow DOM — открыт ли shadowRoot, достаются ли поля."""
from playwright.sync_api import sync_playwright
import json, time, os

STATE = '/root/linkedin-autoapply/auth_state.json'
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
HEADFUL = os.environ.get('HEADFUL') == '1'
print(f'режим: {"HEADFUL (реальный браузер)" if HEADFUL else "headless"}', flush=True)
with open('/root/linkedin-autoapply/data/jobs_scan.json') as f:
    job = json.load(f)[0]

pw = sync_playwright().start()
b = pw.chromium.launch(headless=not HEADFUL, args=[
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

ea = page.query_selector('a[href*="/apply/"]')
print(f'apply найден: {bool(ea)}', flush=True)
ea.click()
time.sleep(7)

# JS-зонд shadow DOM
probe = page.evaluate("""() => {
    const res = {hosts: []};
    // все элементы с shadowRoot
    const all = document.querySelectorAll('*');
    for (const el of all) {
        if (el.shadowRoot) {
            const sr = el.shadowRoot;
            res.hosts.push({
                tag: el.tagName.toLowerCase(),
                id: el.id || '',
                testid: el.getAttribute('data-testid') || '',
                mode: 'open',
                inner_len: (sr.innerHTML || '').length,
                inputs: sr.querySelectorAll('input,select,textarea').length,
                buttons: sr.querySelectorAll('button').length,
                text: (sr.textContent || '').trim().slice(0, 400),
            });
        }
    }
    // interop-outlet отдельно
    const io = document.querySelector('#interop-outlet');
    res.interop = io ? {has_shadow: !!io.shadowRoot, html_len: (io.innerHTML||'').length,
                        text: (io.textContent||'').trim().slice(0,300)} : null;
    return res;
}""")
print('\n=== SHADOW PROBE ===', flush=True)
print(json.dumps(probe, ensure_ascii=False, indent=2), flush=True)

# Playwright piercing: достаёт ли он поля внутри shadow напрямую
print('\n=== Playwright piercing полей (вся страница) ===', flush=True)
for el in page.query_selector_all('input, select, textarea, button'):
    try:
        if not el.is_visible():
            continue
        tag = el.evaluate('e=>e.tagName.toLowerCase()')
        t = (el.inner_text() or '').strip()[:40] if tag == 'button' else ''
        aria = el.get_attribute('aria-label') or ''
        if t or aria:
            print(f'  <{tag}> "{t}" aria="{aria[:50]}"', flush=True)
    except Exception:
        pass

b.close(); pw.stop()
