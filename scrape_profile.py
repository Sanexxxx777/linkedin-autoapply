"""Scrape Aleksandr's LinkedIn profile content for review."""
from playwright.sync_api import sync_playwright
import json, time, random

STATE = '/root/linkedin-autoapply/auth_state.json'
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
OUT_JSON = '/root/linkedin-autoapply/data/profile_full.json'
OUT_HTML = '/root/linkedin-autoapply/data/profile_full.html'
OUT_PNG = '/root/linkedin-autoapply/data/profile_full.png'


def human(a=1.0, b=2.5):
    time.sleep(random.uniform(a, b))


def safe_text(el):
    try:
        t = el.inner_text() or ''
        return ' '.join(t.split())
    except Exception:
        return ''


pw = sync_playwright().start()
b = pw.chromium.launch(headless=True, args=[
    '--no-sandbox', '--disable-blink-features=AutomationControlled',
    '--disable-dev-shm-usage', '--disable-gpu',
])
ctx = b.new_context(storage_state=STATE, user_agent=UA, locale='en-US',
                    viewport={'width': 1366, 'height': 900})
page = ctx.new_page()

print('[scrape] opening profile...', flush=True)
page.goto('https://www.linkedin.com/in/me/', wait_until='domcontentloaded')
human(5, 8)

# scroll to load lazy sections
for _ in range(12):
    page.mouse.wheel(0, 700)
    human(0.6, 1.2)

# back to top for screenshot
page.evaluate('window.scrollTo(0,0)')
human(1, 2)
try:
    page.screenshot(path=OUT_PNG, full_page=False)
except Exception as e:
    print('[scrape] screenshot fail:', e, flush=True)

out = {'url': page.url}

# --- Hero (name, headline, location) ---
try:
    out['name'] = safe_text(page.query_selector('h1'))
except Exception:
    out['name'] = ''
# headline = text directly under h1 in top card
try:
    hl = page.query_selector('div.text-body-medium')
    out['headline'] = safe_text(hl) if hl else ''
except Exception:
    out['headline'] = ''
# location
try:
    locs = page.query_selector_all('span.text-body-small')
    out['location_candidates'] = [safe_text(x) for x in locs[:6] if safe_text(x)]
except Exception:
    out['location_candidates'] = []

# Open To Work badge
try:
    otw = page.query_selector('[aria-label*="Open to work" i], [aria-label*="ищу работу" i]')
    out['open_to_work'] = bool(otw)
except Exception:
    out['open_to_work'] = None

# --- About ---
try:
    about_anchor = page.query_selector('div#about')
    out['about'] = ''
    if about_anchor:
        section = about_anchor.evaluate_handle('el => el.closest("section")')
        if section:
            txt = page.evaluate('s => s.innerText', section)
            out['about'] = ' '.join((txt or '').split())
except Exception as e:
    out['about'] = f'ERR: {e}'

# --- Experience ---
try:
    exp_anchor = page.query_selector('div#experience')
    items = []
    if exp_anchor:
        section = exp_anchor.evaluate_handle('el => el.closest("section")')
        if section:
            entries = section.as_element().query_selector_all('li.artdeco-list__item')
            for e in entries[:15]:
                items.append(safe_text(e))
    out['experience'] = items
except Exception as e:
    out['experience'] = [f'ERR: {e}']

# --- Education ---
try:
    edu_anchor = page.query_selector('div#education')
    items = []
    if edu_anchor:
        section = edu_anchor.evaluate_handle('el => el.closest("section")')
        if section:
            entries = section.as_element().query_selector_all('li.artdeco-list__item')
            for e in entries[:6]:
                items.append(safe_text(e))
    out['education'] = items
except Exception as e:
    out['education'] = [f'ERR: {e}']

# --- Skills ---
try:
    sk_anchor = page.query_selector('div#skills')
    items = []
    if sk_anchor:
        section = sk_anchor.evaluate_handle('el => el.closest("section")')
        if section:
            entries = section.as_element().query_selector_all('li.artdeco-list__item')
            for e in entries[:30]:
                items.append(safe_text(e))
    out['skills'] = items
except Exception as e:
    out['skills'] = [f'ERR: {e}']

# --- Featured ---
try:
    feat_anchor = page.query_selector('div#featured')
    items = []
    if feat_anchor:
        section = feat_anchor.evaluate_handle('el => el.closest("section")')
        if section:
            entries = section.as_element().query_selector_all('li.artdeco-list__item, a')
            seen = set()
            for e in entries[:10]:
                t = safe_text(e)
                if t and t not in seen:
                    seen.add(t)
                    items.append(t)
    out['featured'] = items
except Exception as e:
    out['featured'] = [f'ERR: {e}']

# --- Languages ---
try:
    lang_anchor = page.query_selector('div#languages')
    items = []
    if lang_anchor:
        section = lang_anchor.evaluate_handle('el => el.closest("section")')
        if section:
            entries = section.as_element().query_selector_all('li.artdeco-list__item')
            for e in entries[:6]:
                items.append(safe_text(e))
    out['languages'] = items
except Exception as e:
    out['languages'] = [f'ERR: {e}']

# --- All section anchors (debug) ---
try:
    anchors = page.evaluate(
        '''() => Array.from(document.querySelectorAll('div[id]'))
            .map(d => d.id).filter(Boolean).filter(id => id.length < 30)'''
    )
    out['all_anchors'] = anchors[:40]
except Exception:
    out['all_anchors'] = []

# --- Connections / followers (top card) ---
try:
    stats = page.query_selector_all('ul.pv-top-card--list li, span.t-bold')
    out['top_stats'] = [safe_text(s) for s in stats[:10] if safe_text(s)]
except Exception:
    out['top_stats'] = []

# dump
with open(OUT_JSON, 'w') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

# dump full HTML for fallback parsing
try:
    html = page.content()
    with open(OUT_HTML, 'w') as f:
        f.write(html)
except Exception as e:
    print('[scrape] html save fail:', e, flush=True)

print('[scrape] DONE', flush=True)
print('keys:', list(out.keys()), flush=True)
print('name:', out.get('name'), flush=True)
print('headline:', out.get('headline'), flush=True)
print('about_len:', len(out.get('about', '')), flush=True)
print('experience_n:', len(out.get('experience', [])), flush=True)
print('skills_n:', len(out.get('skills', [])), flush=True)
print('languages_n:', len(out.get('languages', [])), flush=True)
print('featured_n:', len(out.get('featured', [])), flush=True)

b.close()
pw.stop()
