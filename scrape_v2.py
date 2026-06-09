"""LinkedIn profile scrape v2 — wait for SDUI render, read innerText, visit details."""
from playwright.sync_api import sync_playwright
import json, time, random, re

STATE = '/root/linkedin-autoapply/auth_state.json'
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')

OUT_DIR = '/root/linkedin-autoapply/data'


def human(a=0.8, b=1.6):
    time.sleep(random.uniform(a, b))


def deep_scroll(page, steps=18, delta=600):
    for _ in range(steps):
        page.mouse.wheel(0, delta)
        human(0.4, 0.9)


pw = sync_playwright().start()
b = pw.chromium.launch(headless=True, args=[
    '--no-sandbox', '--disable-blink-features=AutomationControlled',
    '--disable-dev-shm-usage', '--disable-gpu',
])
ctx = b.new_context(storage_state=STATE, user_agent=UA, locale='en-US',
                    viewport={'width': 1440, 'height': 900})
page = ctx.new_page()

results = {}

# ---- 1. Main profile page ----
print('[1/5] /in/shulgin-dev/', flush=True)
page.goto('https://www.linkedin.com/in/shulgin-dev/', wait_until='domcontentloaded')
human(8, 12)
deep_scroll(page, steps=20)
human(2, 4)

results['main_url'] = page.url
results['main_text'] = page.evaluate('() => document.body.innerText')
try:
    page.screenshot(path=f'{OUT_DIR}/main_full.png', full_page=True)
except Exception as e:
    print('main screenshot err:', e, flush=True)

# Headlines via specific selectors that exist in LinkedIn DOM
results['main_h1'] = page.evaluate('''() => {
    const h1 = document.querySelector("h1");
    return h1 ? h1.innerText : "";
}''')
results['main_headline'] = page.evaluate('''() => {
    const el = document.querySelector("div.text-body-medium.break-words");
    return el ? el.innerText : "";
}''')
results['main_location'] = page.evaluate('''() => {
    const els = Array.from(document.querySelectorAll("span.text-body-small.inline.t-black--light.break-words"));
    return els.map(e => e.innerText).join(" | ");
}''')

# ---- 2. Details: Experience ----
for slug in ['experience', 'skills', 'education', 'languages']:
    print(f'[next] /details/{slug}/', flush=True)
    url = f'https://www.linkedin.com/in/shulgin-dev/details/{slug}/'
    try:
        page.goto(url, wait_until='domcontentloaded')
        human(6, 9)
        deep_scroll(page, steps=15)
        human(2, 3)
        results[f'{slug}_url'] = page.url
        results[f'{slug}_text'] = page.evaluate('() => document.body.innerText')
        try:
            page.screenshot(path=f'{OUT_DIR}/{slug}.png', full_page=True)
        except Exception as e:
            print(f'{slug} ss err:', e, flush=True)
    except Exception as e:
        print(f'{slug} fail:', e, flush=True)
        results[f'{slug}_error'] = str(e)

# ---- 3. Save ----
with open(f'{OUT_DIR}/profile_v2.json', 'w') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print('[done]', flush=True)
print('main_h1:', results.get('main_h1'), flush=True)
print('main_headline:', results.get('main_headline'), flush=True)
print('main_location:', results.get('main_location'), flush=True)
print('main_text_len:', len(results.get('main_text', '')), flush=True)
print('experience_text_len:', len(results.get('experience_text', '')), flush=True)
print('skills_text_len:', len(results.get('skills_text', '')), flush=True)
print('education_text_len:', len(results.get('education_text', '')), flush=True)
print('languages_text_len:', len(results.get('languages_text', '')), flush=True)

b.close()
pw.stop()
