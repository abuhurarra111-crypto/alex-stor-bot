#!/usr/bin/env bash
# ============================================
#  🤖 Alex Stor Bot — Pydroid 3 One-Click Setup
#  (Pydroid 3 ke Terminal mein yeh script run karo)
# ============================================
set -e
CLEAR='\033[0m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
cecho(){ echo -e "${GREEN}[✓]${CLEAR} $1"; }
yecho(){ echo -e "${YELLOW}[!]${CLEAR} $1"; }
recho(){ echo -e "${RED}[✗]${CLEAR} $1"; }

echo ""
echo "============================================"
echo " 🤖 Alex Stor Bot — Pydroid 3 Installer"
echo "============================================"
echo ""

# Check if we're in a reasonable directory
WORKDIR="$HOME/alex-stor-bot"
mkdir -p "$WORKDIR"
cd "$WORKDIR"

# Step 1: Install Python packages
yecho "Python libraries install ho rahi hain..."
pip install pyTelegramBotAPI APScheduler flask pytz -q 2>&1 | tail -3
cecho "Libraries install ho gayin"

# Step 2: Check for bot.py
if [ ! -f "bot.py" ]; then
    yecho "bot.py download ho raha hai..."
    # Try curl first, then wget, then python
    if command -v curl >/dev/null 2>&1; then
        curl -sL "https://raw.githubusercontent.com/alexstor/alex-stor-bot/main/bot.py" -o bot.py 2>/dev/null || true
    fi
    if [ ! -s bot.py ] && command -v wget >/dev/null 2>&1; then
        wget -q "https://raw.githubusercontent.com/alexstor/alex-stor-bot/main/bot.py" -O bot.py 2>/dev/null || true
    fi
    if [ ! -s bot.py ]; then
        python3 -c "
import urllib.request
try:
    url='https://raw.githubusercontent.com/alexstor/alex-stor-bot/main/bot.py'
    data=urllib.request.urlopen(url,timeout=30).read()
    open('bot.py','wb').write(data)
    print('Downloaded via urllib')
except Exception as e:
    print('FAILED:',e)
    exit(1)
"
    fi
fi

if [ -f bot.py ] && [ -s bot.py ]; then
    cecho "bot.py ready hai ($(wc -l < bot.py) lines)"
else
    recho "bot.py download nahi ho saki — VPN on rakho!"
    exit 1
fi

# Step 3: Set up environment
cat > .env << 'EOF'
BOT_TOKEN=8926710999:AAE5B8_8cY5D8Vn32hMEHIpip3yvFuvOLtw
OWNER_ID=7105782769
TZ=Asia/Karachi
EOF
cecho "Environment save ho gaya"

# Step 4: Create start script
cat > start_pydroid.py << 'PYEOF'
#!/usr/bin/env python3
"""Pydroid 3 ke liye simple launcher — environment set karke bot chala deta hai"""
import os, sys
# Load .env
env_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),".env")
if os.path.exists(env_path):
    for line in open(env_path):
        line=line.strip()
        if line and not line.startswith("#") and "=" in line:
            k,v=line.split("=",1)
            os.environ[k.strip()]=v.strip()
print("="*44)
print(" 🤖 Alex Stor Bot (Pydroid 3)")
print(" ==========================================")
print("  VPN on rakho!  (Cloudflare 1.1.1.1 WARP)")
print("  Band karne ke liye: back button → Stop")
print("="*44)
print("")
# Run bot
import bot
PYEOF
chmod +x start_pydroid.py
cecho "Start script tayyar"

echo ""
echo "============================================"
cecho "  HO GAYA SETUP! 🎉"
echo "============================================"
echo ""
echo "  📍 Ab yeh karo:"
echo "  1. Pydroid 3 mein folder icon tap karo"
echo "  2. Internal Storage → alex-stor-bot open"
echo "  3. start_pydroid.py kholo"
echo "  4. Neeche  ▶️ (Play) button tap karo"
echo ""
echo "  ⚠️  Cloudflare WARP VPN on rakho!"
echo "     (Telegram API Pakistan mein block hai)"
echo ""
