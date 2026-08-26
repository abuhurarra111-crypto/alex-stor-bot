#!/data/data/com.termux/files/usr/bin/bash
echo "🔑 Updating bot token for @Romiie_bot..."
cat > ~/.bashrc.alex << 'ENV'
export BOT_TOKEN="8926710999:AAE5B8_8cY5D8Vn32hMEHIpip3yvFuvOLtw"
export OWNER_ID="7105782769"
export DASH_USER="admin"
export DASH_PASS="alex@stor2026"
export DASH_PORT=5000
export TZ="Asia/Karachi"
ENV
echo "✅ Token updated for @Romiie_bot!"
echo ""
echo "Ab bot chalao:"
echo "  cd ~/alex-stor-bot && ./start.sh"
