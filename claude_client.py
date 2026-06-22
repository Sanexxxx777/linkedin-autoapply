"""LLM клиент — Gemini (бесплатно), Claude API, или Claude CLI.

Приоритет:
1. GEMINI_API_KEY → Google Gemini (бесплатно, 15 RPM)
2. ANTHROPIC_API_KEY → Claude API
3. Claude CLI (подписка)
"""

import json
import os
import time
import subprocess
import requests


def _get_provider() -> str:
    if os.getenv("GROQ_API_KEY"):
        return "groq"
    if os.getenv("GEMINI_API_KEY"):
        return "gemini"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    return "cli"


def _call_groq(prompt: str, model: str = "") -> str:
    import time
    api_key = os.getenv("GROQ_API_KEY")
    model = model or "llama-3.1-8b-instant"

    for attempt in range(3):
        resp = requests.post("https://api.groq.com/openai/v1/chat/completions", json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 2000,
        }, headers={"Authorization": f"Bearer {api_key}"}, timeout=60)

        if resp.status_code == 429:
            wait = (attempt + 1) * 15
            time.sleep(wait)
            continue

        if resp.status_code != 200:
            raise RuntimeError(f"Groq error {resp.status_code}: {resp.text[:300]}")

        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

    raise RuntimeError("Groq rate limit: 3 попытки не удались")


def _call_gemini(prompt: str, model: str = "", json_mode: bool = False) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    model = model or "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    gen_cfg = {"temperature": 0.3, "maxOutputTokens": 4096}
    if json_mode:
        gen_cfg["responseMimeType"] = "application/json"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": gen_cfg,
    }

    # Retry на 503/429/500 — Gemini периодически нестабилен
    last_err = None
    for attempt in range(3):
        try:
            resp = requests.post(url, json=payload, timeout=60)
        except Exception as e:
            last_err = f"network: {e}"
            time.sleep(1.5 * (attempt + 1))
            continue
        if resp.status_code == 200:
            data = resp.json()
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            except (KeyError, IndexError) as e:
                raise RuntimeError(f"Gemini malformed response: {str(data)[:300]}") from e
        if resp.status_code in (429, 500, 502, 503, 504):
            last_err = f"{resp.status_code}: {resp.text[:200]}"
            time.sleep(2.0 * (attempt + 1))
            continue
        # 400/401/403/404 — нет смысла ретраить
        raise RuntimeError(f"Gemini error {resp.status_code}: {resp.text[:300]}")

    raise RuntimeError(f"Gemini error after 3 retries: {last_err}")


def _call_anthropic(prompt: str, model: str, max_tokens: int = 2000) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def _call_cli(prompt: str, model: str = "") -> str:
    cmd = ["claude", "-p", prompt, "--output-format", "text"]
    if model:
        cmd.extend(["--model", model])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
    if result.returncode != 0:
        raise RuntimeError(f"Claude CLI error: {result.stderr[:500]}")
    return result.stdout.strip()


_fallback_chain_cache = None


def _build_fallback_chain() -> list:
    """Строим порядок провайдеров с fallback (кэшируется).

    Groq основной (бесплатно, щедрее по лимитам), между моделями Groq тоже fallback.
    Gemini ОТОДВИНУТ в конец: free-tier 15 RPM быстро упирается в 429 на пакетном
    скоринге (20 вакансий/цикл) — держим как последний запас, не как primary.
    """
    global _fallback_chain_cache
    if _fallback_chain_cache is not None:
        return _fallback_chain_cache

    chain = []
    # Primary: groq, сильная модель первой
    if os.getenv("GROQ_API_KEY"):
        chain.append(("groq", "llama-3.3-70b-versatile"))
        chain.append(("groq", "llama-3.1-8b-instant"))
        chain.append(("groq", "gemma2-9b-it"))
    # Fallback 1: Gemini (если квота восстановилась)
    if os.getenv("GEMINI_API_KEY"):
        chain.append(("gemini", "gemini-2.5-flash"))
    # Fallback 2: Anthropic если есть
    if os.getenv("ANTHROPIC_API_KEY"):
        chain.append(("anthropic", "claude-haiku-4-5-20251001"))
    if not chain:
        chain.append(("cli", ""))

    _fallback_chain_cache = chain
    return chain


def ask_llm(prompt: str, model: str = "", max_tokens: int = 2000) -> str:
    """Вызвать LLM с fallback-цепочкой.

    Если model содержит имя конкретного провайдера (claude-, gemini-, llama-)
    — маршрутизируем на правильный провайдер, а не через общую цепочку.
    """
    # Умный роутинг: если передана конкретная модель — используем правильный провайдер
    if model:
        if model.startswith("claude-") and os.getenv("ANTHROPIC_API_KEY"):
            try:
                return _call_anthropic(prompt, model, max_tokens)
            except Exception as e:
                print(f"  ⚠️  Anthropic/{model} failed: {str(e)[:200]}, fallback to chain")
        elif model.startswith("gemini") and os.getenv("GEMINI_API_KEY"):
            try:
                return _call_gemini(prompt, model)
            except Exception as e:
                print(f"  ⚠️  Gemini/{model} failed: {str(e)[:200]}, fallback to chain")
        elif model.startswith("llama") and os.getenv("GROQ_API_KEY"):
            try:
                return _call_groq(prompt, model)
            except Exception as e:
                print(f"  ⚠️  Groq/{model} failed: {str(e)[:200]}, fallback to chain")

    # Fallback-цепочка
    chain = _build_fallback_chain()
    last_error = None

    for provider, default_model in chain:
        use_model = default_model  # НЕ подставляем model из аргумента — он может быть чужим провайдером
        try:
            if provider == "groq":
                return _call_groq(prompt, use_model)
            elif provider == "gemini":
                return _call_gemini(prompt, use_model)
            elif provider == "anthropic":
                return _call_anthropic(prompt, use_model, max_tokens)
            elif provider == "cli":
                return _call_cli(prompt, use_model)
        except Exception as e:
            last_error = f"{provider}/{use_model}: {str(e)[:200]}"
            print(f"  ⚠️  LLM fallback: {last_error}")
            continue

    raise RuntimeError(f"Все LLM провайдеры недоступны. Последняя ошибка: {last_error}")


def ask_llm_json(prompt: str, model: str = "", max_tokens: int = 2000) -> dict:
    # Если просим Gemini напрямую — включаем JSON-mode (структурированный ответ).
    if model and model.startswith("gemini") and os.getenv("GEMINI_API_KEY"):
        try:
            text = _call_gemini(prompt, model, json_mode=True)
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass  # fall through to general parsing below
        except Exception as e:
            print(f"  ⚠️  Gemini/{model} json-mode failed: {str(e)[:200]}, fallback")
            text = ask_llm(prompt, model, max_tokens)
    else:
        text = ask_llm(prompt, model, max_tokens)

    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        raise ValueError(f"Не удалось распарсить JSON: {text[:300]}")
