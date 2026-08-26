# 📱 Termux Mein Bot Chalanay Ka Poora Tareeqa (Step-by-Step, Bilkul Zero Knowledge)

Bot aap ke liye already tayyar hai, token/ID lag chuka hai. Bas neeche ke steps follow karo.

---

## ✅ Step 0: @BotFather Pe 1 Setting Kar Lo (1 baar, bohat zaruri)

1. Telegram khol kar **@BotFather** search karo
2. `/setprivacy` likho, enter
3. Apna bot choose karo **@Romiie_bot**
4. **Disable** button dabao
5. Done! Is se bot group mein aane wale messages dekh sakega. Agar yeh nahi karoge to auto-reply nahi chale ga.

---

## ✅ Step 1: Termux Download Karo

- Apne phone ke browser mein yeh link kholo: **https://f-droid.org/en/packages/com.termux/**
- "Download APK" button dabao (page mein thora neechay scroll karna hoga)
- APK install kar lo. Agar "Unknown sources" permission maange to de do.
- **Play Store wali Termux mat lena** — woh purani hai, kaam nahi karegi.
- Install ho jaye to ek baar khol lo, 10 second ka first-time setup chalta hai, ruk jao.

---

## ✅ Step 2: Termux Mein 3 Commands (Copy-Paste)

Termux khuli hui screen par neeche diye gaye commands ko **ek ek karke** likho (ya paste kar ke enter dabaao). Har command complete hone ka wait karo phir agli dalo.

### Pehli command (packages install karegi):
```
pkg update -y && pkg upgrade -y && pkg install git python python-pip screen -y
```
- Kabhi kabhi "Do you want to continue?" poochega to `y` likh ke enter dabao.
- Thora time lagega (1-2 minute) — wait.

### Dusri command (bot ke files download karegi GitHub se):
```
cd ~ && git clone https://github.com/abuhurarra111-crypto/alex-stor-bot.git
```
- Download ho jayega. "Receiving objects..." dikhega phir done.

### Teesri command (bot setup karegi, Python libraries install karegi):
```
cd ~/alex-stor-bot && bash setup-termux.sh
```
- 1-2 minute wait, "✅ Ho gaya!" dikh jaye to done.

---

## ✅ Step 3: Bot Chala Do!

Ab bas:
```
./start.sh
```

Screen pe likha hua aayega:
```
🤖 Alex Stor Bot chal raha hai!
Dashboard: http://localhost:5000
User: admin  Pass: alex@stor2026
```

🎉 Mubarak! Bot chalu ho gaya. Isko band mat karo (Ctrl+C mat dabao) jab tak chala rakhna ho.

---

## ✅ Step 4: Telegram Par Bot Test Karo

1. Telegram kholo
2. Apne bot **@Romiie_bot** par jao
3. `/start` likho — bot reply karega welcome message se
4. `/help2` likho — command list aayegi

---

## ✅ Step 5: Apna Pehla Promotion Ad Banayo (5 commands)

Bot se private chat mein yeh karo:

1. `/addpreset promo` likho
2. Button dikhenge "Text", "Photo" wagera — **Text** par tap karo
3. Phir apna asli ad message likho, jaise:
   `🔥 AI Tools saste rates par! ChatGPT Plus, Claude Pro, Midjourney, Gemini aur bohat kuch. DM @alex_stor_but khareedne ke liye!`
   Enter dabao
4. Ab poochega buttons chahiye? Agar chahiye to format:
   `Buy Now | https://t.me/alex_stor_bot`
   agar nahi chahiye to `/skip` likho
5. `/setdefault promo` likho — yeh default ad ban jayega

---

## ✅ Step 6: Apne Group Mein Bot Add Karo (Admin Bana Kar)

1. Apne group mein jao, "Add members" mein ja kar @Romiie_bot add karo
2. Group info mein jao → Administrators → Add admin → @Romiie_bot select karo
3. "Send Messages" permission dena (baqi permissions ki zarurat nahi)
4. Phir bot se private chat mein:
   `/addtarget @yourgroup`
   (apne group ka username dalo ya `/chatid` group mein bhej ke ID nikal lo)

Ab group mein koi bhi message likho — 1 second baad aap ka ad auto-jayega! 🎉

---

## 📱 Dashboard (Phone Browser Se Control)

Chrome browser khol kar yeh kholo: **http://localhost:5000**
- Username: `admin`
- Password: `alex@stor2026`

Yahan se aap:
- Bot on/off kar sakte ho
- Kitne messages gaye stats dekh sakte ho
- Targets/presets list dekh sakte ho
- Backup download kar sakte ho

---

## 🔋 Background Mein Kaise Chalaen? (Phone Band Screen Par Bhi Chalta Rahe)

Agar aap Termux ko band kar ke bhi bot chala rakhna chahte ho:

1. Pehle **Settings → Apps → Termux → Battery** jao → "Unrestricted" / "No optimization" kar do (taake Android band na kare)
2. Termux mein:
   ```
   screen -S bot
   ./start.sh
   ```
3. Bot chalu ho jaye, phir **Ctrl+A dabao, phir D dabao** (ye detach kar dega)
4. Ab Termux ko minimize kar sakte ho, bot background mein chalta rahega
5. Wapas laane ke liye kabhi bhi Termux khol kar:
   ```
   screen -r bot
   ```

---

## 🆘 Agar Koi Masla Aaye to Kya Karna?

- **Package install error** (Step 2 pehli command): Likho `pkg update -y` dobara, phir agli command
- **Git clone failed**: Internet check karo, ya command dobara chalao
- **Bot kuch nahi bhej raha group mein**:
  1. @BotFather se privacy disable ki hai? Check karo
  2. Bot group mein admin hai?
  3. `/addtarget` kiya hai?
  4. `/status` bhejo bot par — "Master ON" dikhna chahiye
- **"Bot can't send messages to bots"**: Normal hai, doosre bots par nahi bhej sakta
- **Command not found**: Command sahi se copy paste nahi hui, dobara likho

---

## 💡 Pehle Din Yehi 3 Settings Kar Lo (Safe Rehne Ke Liye)

Bot se private chat mein:
```
/blacklist addword admin
/blacklist addword mod
/blacklist addword spam
```
Yeh group ke admin/mod ke message par ad nahi jayega — warna aap ko group se nikal dein ge.

```
/delay 5
/randdelay on 6
```
Har ad 5±6 seconds ke random delay se jayega — bot nahi lagega, insaan jaisa feel hoga.

```
/quiet on 23:30 08:00
```
Raat 11:30 se subh 8 tak bot chup rahega.
