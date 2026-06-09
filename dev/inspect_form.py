"""Инспекция Easy Apply формы LinkedIn (READ-ONLY, submit заблокирован).
1. Проверяет валидность сессии (auth_state).
2. Открывает живую Easy Apply вакансию, дампит форму пошагово.
НИКОГДА не нажимает Submit/Отправить — на финальном шаге останавливается и закрывает модалку (Discard).
"""
from playwright.sync_api import sync_playwright
import json, time, random, sys

STATE = '/root/linkedin-autoapply/auth_state.json'
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
JOBS = '/root/linkedin-autoapply/data/jobs_scan.json'
OUT = '/root/linkedin-autoapply/data/form_inspect.json'

# Текст, при котором кнопку НЕЛЬЗЯ нажимать ни при каких условиях
SUBMIT_WORDS = ['submit', 'отправить', 'подать']
NEXT_WORDS = ['next', 'continue', 'далее', 'продолжить', 'review', 'просмотр', 'дальше']

def human(a=1.0, b=2.5):
    time.sleep(random.uniform(a, b))

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
page.set_default_timeout(20000)

# ---- 1. SESSION CHECK ----
print('[1] Проверка сессии...', flush=True)
page.goto('https://www.linkedin.com/feed/', wait_until='domcontentloaded')
human(3, 5)
cur = page.url
print(f'[1] URL после /feed/: {cur}', flush=True)
if any(x in cur for x in ('/login', '/checkpoint', '/authwall', '/uas/login')):
    print('[1] ❌ СЕССИЯ МЕРТВА — нужен relogin через VNC (do_login.py, порт 5903)', flush=True)
    b.close(); pw.stop(); sys.exit(2)
# доп. сигнал — наличие глобального навбара
nav = page.query_selector('.global-nav, header.global-nav, [data-control-name="nav.settings"]')
print(f'[1] ✅ Сессия жива (navbar={"да" if nav else "нет, но не redirect"})', flush=True)

# ---- 2. FORM INSPECT ----
with open(JOBS) as f:
    jobs = json.load(f)

def dump_buttons():
    out = []
    for bel in page.query_selector_all('button'):
        try:
            if not bel.is_visible():
                continue
            txt = (bel.inner_text() or '').strip()
            aria = bel.get_attribute('aria-label') or ''
            if txt or aria:
                out.append({'text': txt[:60], 'aria': aria[:60]})
        except Exception:
            pass
    return out

def dump_fields():
    fields = []
    modal = page.query_selector('div.jobs-easy-apply-modal, [role="dialog"]')
    scope = modal if modal else page
    for el in scope.query_selector_all('input, select, textarea'):
        try:
            if not el.is_visible():
                continue
            tag = el.evaluate('e => e.tagName.toLowerCase()')
            typ = el.get_attribute('type') or ''
            name = el.get_attribute('name') or el.get_attribute('id') or ''
            aria = el.get_attribute('aria-label') or ''
            # подпись через label[for] или ближайший текст
            label = ''
            fid = el.get_attribute('id')
            if fid:
                lab = scope.query_selector(f'label[for="{fid}"]')
                if lab:
                    label = (lab.inner_text() or '').strip()
            opts = []
            if tag == 'select':
                opts = [(o.inner_text() or '').strip() for o in el.query_selector_all('option')][:8]
            fields.append({'tag': tag, 'type': typ, 'name': name[:50],
                           'aria': aria[:80], 'label': (label or aria)[:80], 'options': opts})
        except Exception as e:
            fields.append({'err': str(e)[:60]})
    return fields

def find_easy_apply():
    # LinkedIn SDUI: Easy Apply = <a href=".../apply/?openSDUIApplyFlow=true">Простая подача заявки</a>.
    # Классы обфусцированы (рандомные хэши) — опираемся на href и текст.
    for sel in ['a[href*="openSDUIApplyFlow"]',
                'a[href*="/apply/"]',
                'button:has-text("Простая подача заявки")',
                'button:has-text("Easy Apply")']:
        el = page.query_selector(sel)
        if el and el.is_visible():
            return el
    # fallback: любой видимый a/button с «проста…подач»
    for bel in page.query_selector_all('a, button'):
        try:
            blob = ((bel.inner_text() or '') + ' ' + (bel.get_attribute('aria-label') or '')).lower()
            if 'проста' in blob and 'подач' in blob and bel.is_visible():
                return bel
        except Exception:
            pass
    return None

result = {'job': None, 'steps': []}
for job in jobs:
    print(f'\n[2] Открываю: {job["title"]} [{job["job_id"]}]', flush=True)
    try:
        page.goto(job['url'], wait_until='domcontentloaded')
    except Exception as e:
        print(f'[2] goto err: {e}', flush=True); continue
    time.sleep(9)  # SDUI рендерит apply-кнопку поздно
    try:
        page.wait_for_selector('a[href*="/apply/"], button:has-text("Простая подача заявки")', timeout=12000)
    except Exception:
        pass
    ea = find_easy_apply()
    if not ea:
        # диагностика: какие вообще apply-кнопки есть на странице
        diag = []
        for bel in page.query_selector_all('button'):
            try:
                if not bel.is_visible():
                    continue
                t = (bel.inner_text() or '').strip()
                a = bel.get_attribute('aria-label') or ''
                cl = bel.get_attribute('class') or ''
                blob = (t + ' ' + a).lower()
                if any(w in blob for w in ('apply', 'подать', 'откликн', 'easy')):
                    diag.append({'text': t[:50], 'aria': a[:50], 'class': cl[:60]})
            except Exception:
                pass
        print(f'[2] нет Easy Apply. apply-кнопки на странице: {diag if diag else "вообще нет"}', flush=True)
        continue
    print('[2] ✅ Easy Apply найдена, открываю модалку', flush=True)
    result['job'] = job
    ea.click()
    time.sleep(6)  # SDUI apply-flow модалка

    # пошаговый дамп
    for step in range(1, 8):
        human(1.5, 3)
        title_el = page.query_selector('div[role="dialog"] h3, .jobs-easy-apply-modal h3, h2')
        step_title = (title_el.inner_text().strip() if title_el else '')
        fields = dump_fields()
        btns = dump_buttons()
        print(f'\n  --- ШАГ {step}: "{step_title}" ---', flush=True)
        print(f'  полей: {len(fields)}', flush=True)
        for fld in fields:
            print(f'    [{fld.get("tag")}/{fld.get("type")}] {fld.get("label") or fld.get("name")} {("opts="+str(fld["options"])) if fld.get("options") else ""}', flush=True)
        print(f'  кнопки: {[bb["text"] or bb["aria"] for bb in btns]}', flush=True)
        result['steps'].append({'step': step, 'title': step_title, 'fields': fields, 'buttons': btns})

        # ищем кнопку продвижения, НИКОГДА не submit
        nxt = None
        for bel in page.query_selector_all('div[role="dialog"] button, .jobs-easy-apply-modal button'):
            try:
                if not bel.is_visible():
                    continue
                t = ((bel.inner_text() or '') + ' ' + (bel.get_attribute('aria-label') or '')).lower()
                if any(w in t for w in SUBMIT_WORDS):
                    continue  # СТОП — это submit
                if any(w in t for w in NEXT_WORDS):
                    nxt = bel; break
            except Exception:
                pass
        # проверяем не финал ли (есть submit-кнопка)
        has_submit = False
        for bel in page.query_selector_all('div[role="dialog"] button, .jobs-easy-apply-modal button'):
            try:
                t = ((bel.inner_text() or '') + ' ' + (bel.get_attribute('aria-label') or '')).lower()
                if bel.is_visible() and any(w in t for w in SUBMIT_WORDS):
                    has_submit = True; break
            except Exception:
                pass
        if has_submit:
            print('\n  🛑 Достигнут шаг с кнопкой SUBMIT — останавливаюсь, НЕ отправляю', flush=True)
            break
        if not nxt:
            print('\n  ⚠️ Кнопка продвижения не найдена — стоп', flush=True)
            break
        print(f'  → жму: "{nxt.inner_text().strip()}"', flush=True)
        nxt.click()

    # закрываем модалку без отправки
    try:
        dismiss = page.query_selector('button[aria-label*="Dismiss"], button[aria-label*="Закрыть"]')
        if dismiss:
            dismiss.click(); human(1, 2)
            discard = page.query_selector('button:has-text("Discard"), button:has-text("Отменить")')
            if discard:
                discard.click()
        print('[2] модалка закрыта (без отправки)', flush=True)
    except Exception as e:
        print(f'[2] close err: {e}', flush=True)
    break  # инспектируем одну вакансию

with open(OUT, 'w') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f'\n[done] сохранено в {OUT}', flush=True)
b.close(); pw.stop()
