#!/data/data/com.termux/files/usr/bin/bash
set -e
echo "============================================"
echo " 🤖 Alex Stor Bot — Termux Installer"
echo "============================================"
echo ""
echo "[1/4] Packages install ho rahe hain..."
pkg update -y >/dev/null 2>&1 || true
pkg upgrade -y >/dev/null 2>&1 || true
pkg install python python-pip git screen tzdata -y >/dev/null 2>&1
echo "[2/4] Python libraries install..."
# Note: pip upgrade mat karo (Termux mein forbidden hai)
pip install pyTelegramBotAPI APScheduler flask pytz -q 2>&1 | tail -5 || true
echo "[3/4] Environment save..."
mkdir -p ~/alex-stor-bot
cat > ~/.bashrc.alex << 'EOF'
export BOT_TOKEN="8926710999:AAE5B8_8cY5D8Vn32hMEHIpip3yvFuvOLtw"
export OWNER_ID="7105782769"
export DASH_USER="admin"
export DASH_PASS="alex@stor2026"
export DASH_PORT=5000
export TZ="Asia/Karachi"
EOF
if ! grep -q "bashrc.alex" ~/.bashrc 2>/dev/null; then
    echo 'source ~/.bashrc.alex' >> ~/.bashrc
fi
source ~/.bashrc.alex
echo "[4/4] Start script bana raha hoon..."
cat > ~/alex-stor-bot/start.sh << 'STARTEOF'
#!/data/data/com.termux/files/usr/bin/bash
cd ~/alex-stor-bot
source ~/.bashrc.alex
echo ""
echo "============================================"
echo " 🤖 Alex Stor Bot chal raha hai!"
echo " Dashboard: http://localhost:5000"
echo " User: admin  Pass: alex@stor2026"
echo " Band karo: Ctrl+C"
echo " Background: screen -S bot -> ./start.sh -> Ctrl+A then D"
echo "============================================"
echo ""
python3 bot.py
STARTEOF
chmod +x ~/alex-stor-bot/start.sh
echo ""
echo "✅ Ho gaya!"
echo "Bot chalanay ke liye: cd ~/alex-stor-bot && ./start.sh"
