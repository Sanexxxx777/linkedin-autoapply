"""Тест канала уведомлений: шлёт в HH-бота список найденных LinkedIn вакансий."""
import os, json, requests
from dotenv import load_dotenv

load_dotenv('/root/hh-autoapply/.env')
TOKEN = os.getenv('TG_BOT_TOKEN')
CHAT = os.getenv('TG_CHAT_ID')

jobs = json.load(open('/root/linkedin-autoapply/data/jobs_scan.json'))
lines = [f"• <b>{j['title']}</b> — {j['company']}" for j in jobs[:10]]
text = ("\U0001F517 <b>[LinkedIn]</b> канал уведомлений подключён ✅\n\n"
        f"Тестовый прогон: найдено <b>{len(jobs)}</b> Easy Apply вакансий (dry-run, без откликов):\n\n"
        + "\n".join(lines)
        + "\n\n<i>Боевые отклики — после отлёжки аккаунта (2-3 дня). Сейчас только разведка.</i>")

r = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                  json={'chat_id': CHAT, 'text': text, 'parse_mode': 'HTML',
                        'disable_web_page_preview': True}, timeout=15)
print('TG status:', r.status_code, '| ok:', r.json().get('ok'))
