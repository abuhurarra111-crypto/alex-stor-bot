# 🤖 Alex Stor Bot — AI Tools Shop Promotion Bot
Telegram bot for promoting your AI tools shop across groups/channels.

## 📱 Termux Mein Install Karne Ka Poora Tareeqa (Asaan)
Neeche di gayi commands ko Termux mein ek ek karke paste karo:

### Step 1: Termux install
F-Droid se Termux download karo: https://f-droid.org/en/packages/com.termux/
(Play Store wali mat lena)

### Step 2: @BotFather settings (zaruri)
- Bot banaya howa hai: @Romiie_bot
- @BotFather par ja kar **/setprivacy** → bot select → **Disable** kar do
  (warna bot group ke messages nahi dekh sakega)

### Step 3: Termux mein yeh 3 commands chalao
```bash
pkg update -y && pkg upgrade -y && pkg install git -y
```
Enter dabayein, kabhi 'y/n' pooche to y dabao.

```bash
cd ~ && git clone https://github.com/abuhurarra111-crypto/alex-stor-bot.git
```
(Repo download ho jayegi)

```bash
cd ~/alex-stor-bot && bash setup-termux.sh
```
(2 minute wait karein, packages install ho jayenge)

### Step 4: Bot chalao
```bash
./start.sh
```
Mubarak! Bot chalu ho gaya.

### Step 5: Test karo
Telegram mein apne bot @Romiie_bot par /start bhejo.

## 🔑 Dashboard
Phone ke browser mein: http://localhost:5000
- Username: `admin`
- Password: `alex@stor2026`

## 📖 Pehla Setup (zaruri commands)
Bot se private chat mein:
1. `/addpreset promo`  →  phir apna promotion message likho  →  buttons ke liye format `Text|https://url` ya /skip
2. `/setdefault promo`
3. Apne group mein bot ko admin banao
4. `/addtarget @yourgroup`
5. Group mein kuch bhejo — 1 sec baad auto-reply aa jayega!

## 🛡️ Important
- @BotFather se privacy DISABLE karna mat bhoolein
- Bot ko har group mein admin banana padta hai
- Background chalanay ke liye: `screen -S bot && ./start.sh` phir Ctrl+A then D
- Band karne ke liye Ctrl+C dabao
- Problem aaye to bhai se rabta karo!

## ⚠️ Token Security Note
Setup ke baad is token ko private rakhna. Agar kabhi token leak ho jaye to @BotFather se /token se naya le lena.
