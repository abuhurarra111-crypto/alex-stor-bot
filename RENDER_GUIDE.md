# 🚀 Render.com pe Bot Deploy Karne Ka Step-by-Step Guide

Render free tier pe bot 24/7 chalta hai, phone on/off ya VPN ki koi zaroorat nahi.

---

## ⚠️ Pehle ek zaruri kaam (GitHub Repo)
Render code ko GitHub se leta hai, is liye code ko GitHub pe push karna zaroori hai.

### Agar aapke paas pehle se repo hai:
1. GitHub pe login karo → https://github.com
2. `alex-stor-bot` wali repo kholo
3. **Add file** → **Upload files** → is bot.py file (jo maine abhi update ki hai) ko upload karo → **Commit changes**
4. Saath mein `requirements.txt`, `Procfile` bhi upload kar do

### Agar naya repo banana hai:
1. GitHub → **New repository** → naam do `alex-stor-bot` → Public → Create
2. Apne phone par Termux/Pydroid mein:
   ```bash
   cd ~/alex-stor-bot
   git add .
   git commit -m "render ready"
   git branch -M main
   git remote set-url origin https://github.com/APNA_USERNAME/alex-stor-bot.git
   git push -u origin main
   ```

---

## 🚀 Render Setup Steps (Browser mein karo, phone ya PC se)

### Step 1: Render pe account banao
1. https://render.com pe jao
2. **Get Started for Free** → GitHub se sign up karo (asaan hai)
3. Email verify kar lo

### Step 2: New Web Service
1. Dashboard mein **+ New** → **Web Service** click karo
2. "Build and deploy from a Git repository" select karo
3. GitHub connect karo (agar pooche to)
4. Apna `alex-stor-bot` repo select karo → **Connect**

### Step 3: Service Settings
Yeh sab fill karo:

| Field | Value |
|-------|-------|
| **Name** | `alex-stor-bot` (kuch bhi rakh sakte ho) |
| **Region** | `Oregon (US West)` ya `Frankfurt` (koi bhi) |
| **Branch** | `main` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python bot.py` |
| **Instance Type** | **Free** (neeche scroll kar ke free select karo) |

### Step 4: Environment Variables (SABSE ZAROORI!)
**Advanced** button click karo → **Add Environment Variable** aur yeh 3 vars add karo:

| Key | Value |
|-----|-------|
| `BOT_TOKEN` | `8926710999:AAE5B8_8cY5D8Vn32hMEHIpip3yvFuvOLtw` |
| `OWNER_ID` | `7105782769` |
| `PYTHON_VERSION` | `3.11.9` |

### Step 5: Deploy!
**Create Web Service** button dabao. Render build start kar dega.

- Build 1-2 minute lega
- Logs mein dekh sakte ho
- Jab "**Deploy live for ...**" aur "Your service is live 🎉" dikhe, bot chal raha hai!

---

## ✅ Verify Karo
1. Telegram mein jao → @Romiie_bot
2. `/start` bhejo
3. Menu khul jayega! Bas bot ab cloud pe 24/7 chalta rahega.

Dashboard bhi Render ke URL pe live hoga (e.g. `https://alex-stor-bot.onrender.com`), wahan pe ja ke `admin` / `alex@stor2026` se login kar ke stats dekh sakte ho.

---

## ⚠️ Important Notes (Free Tier)

1. **Data persistence**: Render free tier pe disk temporary hoti hai — matlab jab bhi service restart/deploy hoti hai, `data.json` reset ho jata hai (sab ads/targets/stats erase ho jate hain). 
   - **Hal**: `/backup` command se kabhi bhi backup JSON file le lo
   - Naye deploy ke baad `/restore` se wapas upload kar do
   - Agar permanent chahiye to Render paid ($7/month) ya Railway use karo

2. **Cold start**: Kabhi kabhi free tier thoda slow start hota hai (1-2 minute), lekin normal hai

3. **Auto-deploy**: Jab bhi aap GitHub pe naya code push karoge, Render khud ba khud re-deploy kar lega

4. **VPN ki zaroorat nahi**: Render cloud server US/EU mein hai, wahan Telegram block nahi hai — no WARP needed!

---

## 🔧 Agar koi error aaye
- Render dashboard mein **Logs** tab pe ja ke dekh lo kya error hai
- Screenshot bhejo, main fix kar doonga
- Common issues:
  - **Token error**: BOT_TOKEN env var sahi se dala hai?
  - **Build fail**: requirements.txt check karo
  - **Not starting**: Start command `python bot.py` hai na?

---

## 🎯 Post-Setup (Bot ke saath karo)
Bot chalu ho jaye to Telegram mein @Romiie_bot se:
1. `/menu` bhejo → settings configure karo
2. @BotFather se **privacy mode disable** karo (Groups Settings → Turn off) — warna bot group messages nahi dekh sakega
3. @BotFather se commands set karo: `/setcommands` → bot select → yeh text bhejo:
   ```
   start - Start the bot
   menu - Open main menu
   help2 - List all commands
   status - Bot status
   stats - Show stats
   backup - Download backup
   ```
4. Apne groups mein bot ko **admin** banao
5. Pehla ad banao → target add karo → `/sendnow` test karo!
