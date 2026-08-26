# 🤖 Alex Stor Bot — Pydroid 3 Guide (No Command Line!)

Pydroid 3 sab se aasan tareeqa hai Android phone pe bot chalanay ke liye. Koi Termux commands nahi, bas button tap karo.

---

## Step 1: Install Apps (1 time)

1. **Play Store** open karo
2. Search **"Pydroid 3"** (by IIEC) — install karo (~30 MB)
3. Agar already nahi hai to **"1.1.1.1 WARP"** (by Cloudflare) bhi install rakho — VPN ke liye zaroori hai

---

## Step 2: Download bot.py

Pydroid 3 install ho jaye, to bot.py file download karo:
- Is repo mein jo `bot.py` file hai, usko apne phone ke **Download** folder mein copy/ save kar lo
- File size ~80 KB hai, 1586 lines

**Aasan tareeqa**: GitHub se directly download kar lo browser mein:
```
https://raw.githubusercontent.com/alexstor/alex-stor-bot/main/bot.py
```
(Link pe jao, long-press → Save link as → `bot.py` naam se Download folder mein save karo)

---

## Step 3: Pydroid 3 Setup

1. **Pydroid 3** open karo
2. Top bar mein pehla icon (📁 folder) tap karo
3. **"Open"** choose karo
4. Apne **Download** folder mein jao → `bot.py` select karo
5. Ab code khul jayega
6. Neeche right side mein **yellow ▶️ Play button** hai — USKO MAT TAP KARO ABHI

---

## Step 4: Pehli baar libraries install karo

1. Menu ≡ (top left) → **Pip** tap karo
2. Search box mein yeh ek ek karke search karo aur **Install** tap karo:
   - `pyTelegramBotAPI`
   - `APScheduler`
   - `flask`
   - `pytz`
3. Sab install ho jayein to wait karo (1-2 minute)

---

## Step 5: Set Bot Token

1. Menu ≡ → **Terminal** tap karo
2. Terminal mein yeh type karo (apna actual bot token dalo — jo @BotFather se liya tha):
   ```bash
   export BOT_TOKEN="YOUR_BOT_TOKEN_YAHAN"
   export OWNER_ID="7105782769"
   export TZ="Asia/Karachi"
   ```
   _(Yeh @Romiie_bot ka token already bot.py mein built-in hai, to agar wohi bot hai to yeh step skip kar sakte ho)_

---

## Step 6: Bot CHALAO! 🚀

1. Ab **Editor** tab pe wapas jao (bot.py khula hua hoga)
2. Neeche **▶️ yellow Play button** tap karo
3. Console khulega aur bot start ho jayega!
4. Aap dekhoge: `🤖 Alex Stor Bot v3 started as @Romiie_bot`

---

## Important Notes

✅ **WARP VPN on rakho** (1.1.1.1 app open → big button blue kar lo) — warna Telegram connect nahi hoga (Pakistan mein block hai)

✅ Background mein chalta rahega jab tak Pydroid 3 open hai

❌ **Battery optimization off kar do** Pydroid 3 ke liye (Settings → Apps → Pydroid 3 → Battery → Unrestricted) — warna phone screen off hote hi bot band ho jayega

✅ Agar bot stop ho jaye to bas dubara ▶️ Play button tap karo

---

## Agar 24/7 chahiye cloud hosting (FREE):

Agar apne phone ko chala ke nahi rakhna chahte, ye free cloud hosting options dekho:
- **render.com** — Free tier, GitHub se auto deploy (1 command mein)
- **koyeb.com** — Free tier always-on
- **pythonanywhere.com** — Free, beginner friendly

Inke liye bhi bata sakta hoon setup chahiye to bolo!

---

## Shortcuts

| Kaam | Button |
|---|---|
| Bot start | ▶️ Play button |
| Bot stop | ⏹️ Stop button |
| Console dekhna | Bottom "Terminal" tab |
| Naya file | ➕ folder icon |
