#!/usr/bin/env python3
"""RingkasBot — Telegram utility bot: summarize long text & article links.

Business model: 3 free summaries, then pay-per-use credits bought with
Telegram Stars (currency XTR, Telegram's native digital-goods payment — no
external payment provider, no KYC for the bot owner).

Stdlib only: Bot API over urllib long-polling, SQLite ledger, extractive
summarizer. Run: BOT_TOKEN=... python3 bot.py
Optional: ADMIN_ID=<telegram user id> enables /stats.
"""
import html
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error

from store import Store
from summarizer import summarize, looks_like_url

TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0") or 0)
API = f"https://api.telegram.org/bot{TOKEN}"
store = Store(os.environ.get("DB_PATH", "ringkasbot.db"))

PACKAGES = {  # payload -> (credits, stars)
    "pack10": (10, 15),
    "pack30": (30, 39),
    "pack100": (100, 99),
}

WELCOME = (
    "👋 <b>RingkasBot</b> — long text in, short summary out.\n\n"
    "Send me a long text, or a link to an article, and I'll summarize it.\n"
    "🎁 You start with <b>3 free summaries</b>. After that, 1 credit = 1 summary, "
    "top up anytime with /buy (Telegram Stars).\n\n"
    "Commands: /balance · /buy · /help"
)
HELP = (
    "Send any long text (200+ characters) or an article URL and I'll return a summary.\n"
    "• /balance — your free summaries and credits\n"
    "• /buy — credit packages (Telegram Stars)\n"
    "Summaries are extractive: the most important original sentences, in order. "
    "Works in English and Indonesian."
)


def call(method, **params):
    data = json.dumps(params).encode()
    req = urllib.request.Request(f"{API}/{method}", data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=70) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print("API error", method, e.code, e.read()[:200], file=sys.stderr)
        return {"ok": False}
    except Exception as e:  # network hiccup / dropped connection: caller retries
        print("API unreachable", method, type(e).__name__, file=sys.stderr)
        return {"ok": False}


def send(chat_id, text, **kw):
    return call("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML", **kw)


def fetch_article(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 RingkasBot"})
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read(600_000).decode("utf-8", errors="replace")
    raw = re.sub(r"(?is)<(script|style|nav|footer|header).*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return html.unescape(re.sub(r"\s+", " ", raw)).strip()


def handle_text(chat_id, uid, text):
    if not store.can_afford(uid):
        send(chat_id, "You're out of free summaries and credits. Top up with /buy — "
                      "10 summaries for 15 ⭐, no subscription.")
        return
    body = text
    if looks_like_url(text):
        send(chat_id, "Fetching the article…")
        try:
            body = fetch_article(text.strip())
        except Exception:
            send(chat_id, "I couldn't fetch that page. Paste the article text instead.")
            return
    if len(body) < 200:
        send(chat_id, "That text is already short — send something longer (200+ characters) "
                      "and I'll compress it. No charge for this one.")
        return
    summary = summarize(body, max_sentences=5)
    charged = store.charge(uid)
    if charged is None:  # race-safe fallback
        send(chat_id, "You're out of credits. Top up with /buy.")
        return
    b = store.balance(uid)
    send(chat_id, f"📝 <b>Summary</b>\n\n{html.escape(summary)}\n\n"
                  f"<i>Charged: {'free trial' if charged == 'free' else '1 credit'} · "
                  f"Free left: {b['free_left']} · Credits: {b['credits']}</i>")


def handle_buy(chat_id, uid):
    kb = {"inline_keyboard": [[
        {"text": f"{c} summaries — {s} ⭐", "callback_data": p}]
        for p, (c, s) in [("pack10", PACKAGES["pack10"])] ]}
    # one row per package for readability
    kb = {"inline_keyboard": [
        [{"text": f"{c} summaries — {s} ⭐", "callback_data": p}]
        for p, (c, s) in PACKAGES.items()]}
    send(chat_id, "Choose a credit package. Payment uses Telegram Stars — "
                  "secure, handled by Telegram, refundable per Telegram's terms.",
         reply_markup=kb)


def handle_callback(cb):
    data = cb.get("data", "")
    uid = cb["from"]["id"]
    chat_id = cb["message"]["chat"]["id"]
    call("answerCallbackQuery", callback_query_id=cb["id"])
    if data in PACKAGES:
        credits, stars = PACKAGES[data]
        call("sendInvoice", chat_id=chat_id,
             title=f"RingkasBot — {credits} summary credits",
             description=f"{credits} RingkasBot summary credits. Never expire.",
             payload=data, currency="XTR",
             prices=[{"label": f"{credits} credits", "amount": stars}])


def handle_update(upd):
    if "pre_checkout_query" in upd:
        call("answerPreCheckoutQuery", pre_checkout_query_id=upd["pre_checkout_query"]["id"], ok=True)
        return
    msg = upd.get("message") or {}
    if "successful_payment" in msg:
        uid = msg["from"]["id"]
        pay = msg["successful_payment"]
        payload = pay.get("invoice_payload", "")
        if payload in PACKAGES:
            credits, _ = PACKAGES[payload]
            added = store.add_payment(uid, pay["telegram_payment_charge_id"],
                                      credits, pay["total_amount"])
            if added:
                b = store.balance(uid)
                send(msg["chat"]["id"], f"✅ Payment received — {credits} credits added. "
                                        f"Your balance: {b['credits']} credits.")
        return
    if "callback_query" in upd:
        handle_callback(upd["callback_query"])
        return
    if not msg or "text" not in msg:
        return
    chat_id, uid, text = msg["chat"]["id"], msg["from"]["id"], msg["text"].strip()
    if text.startswith("/start"):
        store.balance(uid)  # register user
        send(chat_id, WELCOME)
    elif text.startswith("/help"):
        send(chat_id, HELP)
    elif text.startswith("/balance"):
        b = store.balance(uid)
        send(chat_id, f"🎁 Free summaries left: <b>{b['free_left']}</b>\n"
                      f"⭐ Credits: <b>{b['credits']}</b>\nTop up with /buy.")
    elif text.startswith("/buy"):
        handle_buy(chat_id, uid)
    elif text.startswith("/stats") and uid == ADMIN_ID and ADMIN_ID:
        s = store.stats()
        send(chat_id, f"Users: {s['users']} · Summaries served: {s['summaries']} · "
                      f"Stars earned: {s['stars_earned']} ⭐")
    elif text.startswith("/"):
        send(chat_id, "Unknown command. " + HELP)
    else:
        handle_text(chat_id, uid, text)


def main():
    if not TOKEN:
        print("Set BOT_TOKEN first (get it from @BotFather).", file=sys.stderr)
        return 2
    me = call("getMe")
    print("Running as", me.get("result", {}).get("username"))
    offset = 0
    while True:
        res = call("getUpdates", offset=offset, timeout=60,
                   allowed_updates=["message", "callback_query", "pre_checkout_query"])
        for upd in res.get("result", []):
            offset = upd["update_id"] + 1
            try:
                handle_update(upd)
            except Exception as e:  # one bad update must never kill the bot
                print("update error:", e, file=sys.stderr)
        if not res.get("ok"):
            time.sleep(3)


if __name__ == "__main__":
    raise SystemExit(main())
