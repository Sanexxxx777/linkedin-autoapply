"""LinkedIn login: ловим сессию по cookie li_at, сохраняем auth_state.
Окно НЕ закрывается по таймауту — ждём вход сколько нужно.
Логинишься РУКАМИ в окне Chromium на VNC display :3."""
from playwright.sync_api import sync_playwright
import os, time

STATE_FILE = '/root/linkedin-autoapply/auth_state.json'
UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')

pw = sync_playwright().start()
browser = pw.chromium.launch(
    headless=False,
    args=['--no-sandbox', '--disable-blink-features=AutomationControlled'],
)
context = browser.new_context(
    viewport={'width': 1280, 'height': 780},
    user_agent=UA,
    locale='en-US',
)
page = context.new_page()

print('[login] Открываю https://www.linkedin.com/login', flush=True)
page.goto('https://www.linkedin.com/login')
print('[login] ЗАЛОГИНЬСЯ В ЭТОМ окне Chromium (VNC display :3).', flush=True)
print('[login] Окно НЕ закроется само. Слежу за cookie li_at...', flush=True)

last_url = ''
i = 0
while True:
    time.sleep(1)
    i += 1
    try:
        url = page.url
        cookies = context.cookies()
    except Exception as e:
        print(f'[{i}s] окно закрыто/ошибка: {e}', flush=True)
        break

    if url != last_url:
        print(f'[{i}s] URL: {url}', flush=True)
        last_url = url
    elif i % 30 == 0:
        print(f'[{i}s] heartbeat, URL: {url}', flush=True)

    has_li_at = any(c['name'] == 'li_at' and c.get('value') for c in cookies)
    off_login = '/login' not in url and '/checkpoint' not in url and 'linkedin.com' in url

    if has_li_at and off_login:
        time.sleep(2)
        try:
            page.goto('https://www.linkedin.com/feed/', wait_until='domcontentloaded')
            time.sleep(3)
            current = page.url
            if '/login' in current or '/checkpoint' in current or '/authwall' in current:
                print(f'[{i}s] li_at есть, но редирект на {current} — ещё не валидно', flush=True)
                continue
            page.screenshot(path='/tmp/li_login_verify.png')
            print(f'[{i}s] LOGGED IN OK ({current})', flush=True)
        except Exception as e:
            print(f'[{i}s] verify err: {e}', flush=True)
            continue
        context.storage_state(path=STATE_FILE)
        size = os.path.getsize(STATE_FILE)
        print(f'[login] СОХРАНЕНО в {STATE_FILE} ({size} байт)', flush=True)
        break

print('[login] Закрываю через 10 сек', flush=True)
time.sleep(10)
browser.close()
pw.stop()
print('[login] Готово!', flush=True)
