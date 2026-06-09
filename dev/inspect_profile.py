"""Инспекция профиля: собрать кнопки редактирования (About/Services/Featured).
Read-only, лёгкая по памяти (без full_page)."""
from playwright.sync_api import sync_playwright
import json, time, random

STATE = '/root/linkedin-autoapply/auth_state.json'
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')

def human(a=1.5, b=3.5):
    time.sleep(random.uniform(a, b))

pw = sync_playwright().start()
b = pw.chromium.launch(headless=True, args=[
    '--no-sandbox', '--disable-blink-features=AutomationControlled',
    '--disable-dev-shm-usage', '--disable-gpu',
])
ctx = b.new_context(storage_state=STATE, user_agent=UA, locale='en-US',
                    viewport={'width': 1366, 'height': 900})
page = ctx.new_page()

print('[inspect] открываю профиль...', flush=True)
page.goto('https://www.linkedin.com/in/me/', wait_until='domcontentloaded')
human(4, 7)

# мягкий скролл вниз (имитация чтения), подгружает секции
for y in (400, 900, 1500, 2200):
    page.mouse.wheel(0, 500)
    human(1, 2)

page.screenshot(path='/tmp/li_prof2.png')

# собрать все кнопки с aria-label
btns = page.query_selector_all('button[aria-label], a[aria-label]')
labels = []
for el in btns:
    try:
        lab = el.get_attribute('aria-label') or ''
        if lab and any(k in lab.lower() for k in
                       ['edit','изм','редакт','инфо','about','add','доб','услуг',
                        'service','featured','избран','раздел','section']):
            labels.append(lab)
    except Exception:
        pass

# секции профиля по id/anchor
sections = []
for sec in page.query_selector_all('section[data-section], div#about, section.artdeco-card'):
    try:
        h = sec.query_selector('h2, h3')
        if h:
            sections.append((h.inner_text() or '').strip()[:40])
    except Exception:
        pass

out = {'edit_labels': sorted(set(labels)),
       'sections': [s for s in sections if s][:20],
       'url': page.url, 'lang_ru': 'инфо' in (' '.join(labels)).lower()}
print(json.dumps(out, ensure_ascii=False, indent=2), flush=True)
with open('/root/linkedin-autoapply/data/profile_inspect.json','w') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
human()
b.close(); pw.stop()
print('[inspect] готово', flush=True)
