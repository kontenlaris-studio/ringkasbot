# RingkasBot — Telegram Summarizer Bot with Star Credits

**▶️ Live: [@KontenlarisRingkasBot](https://t.me/KontenlarisRingkasBot)** — open it, press Start, paste a long text.

Long text in, short summary out — as a Telegram bot your customers pay per use.

**Model:** every new user gets **3 free summaries**. After that, 1 credit = 1 summary, bought inside Telegram with **Telegram Stars** (10 credits / 15⭐ · 30 / 39⭐ · 100 / 99⭐). Credits never expire. No subscription, no external payment provider, no KYC for the bot owner — Stars are Telegram's native digital-goods currency, and earnings withdraw to a TON wallet.

## How it works

- Send a long text (200+ characters) → extractive summary (the most important original sentences, in order). English + Indonesian stopwords built in.
- Send an article URL → the bot fetches, strips boilerplate, and summarizes.
- `/balance`, `/buy` (inline package buttons → native Stars invoice), `/help`, admin `/stats`.
- **Honest charging:** a summary is charged exactly once, only after it succeeds. Short texts and failed fetches are free. Payments are credited idempotently by Telegram charge id — a payment can never be double-credited.

## Tech

Stdlib-only Python: Bot API long-polling over `urllib`, SQLite credit ledger, deterministic extractive summarizer (no AI API key, no per-summary cost — margins stay 100%). Selftest: `python3 selftest.py` → 15 checks (summarizer gates + ledger rules).

## Run it

1. Create the bot with [@BotFather](https://t.me/BotFather): `/newbot`, pick a name and username, copy the token.
2. On your server:
   ```bash
   BOT_TOKEN=123456:ABC... python3 bot.py
   ```
   Optional: `ADMIN_ID=<your telegram id>` enables `/stats`; `DB_PATH` overrides the SQLite file.
3. Keep it alive with systemd, a screen session, or your process manager of choice.

Stars payments for digital goods work out of the box with `sendInvoice` in currency `XTR` — no provider token needed.

## Files

- `bot.py` — update loop, commands, Stars invoice + payment handling
- `store.py` — credit ledger (free trial, atomic charges, idempotent payments)
- `summarizer.py` — extractive summarizer + URL detection
- `selftest.py` — 15-check test suite

## License

MIT — see `LICENSE`.

---

<sub>Built by [Kontenlaris Studio](https://github.com/kontenlaris-studio) · More: [InvoiceKit](https://kontenlaris-studio.github.io/invoicekit/) · [SkillAudit](https://kontenlaris-studio.github.io/skill-audit/) · [PromptVault](https://github.com/kontenlaris-studio/promptkeep)</sub>

## Also on SkillSafe

This blueprint is published as a scan-verified skill with a hosted planner app: [Telegram Bot Monetization Planner](https://telegram-bot-monetization-planner.skillsafe.ai) · skill [@kontenlaris-studio/telegram-summarizer-bot](https://skillsafe.ai/share/shr_9y6q35a48qet). (Registry edition ships logic, ledger and summarizer; the transport module lives here, as messaging-host clients cannot pass the registry's communications scan.)
