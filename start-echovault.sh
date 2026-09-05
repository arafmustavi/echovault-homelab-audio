#!/data/data/com.termux/files/usr/bin/bash

echo "================================="
echo " EchoVault Termux Installer"
echo "================================="

pkg update -y
pkg upgrade -y

echo "[1/6] Installing packages..."

pkg install -y \
python \
git \
ffmpeg \
wget \
curl \
nano \
unzip

echo "[2/6] Installing Python packages..."

pip install --upgrade pip

pip install \
yt-dlp \
flask \
gunicorn \
requests

echo "[3/6] Enabling storage..."

termux-setup-storage

sleep 5

mkdir -p ~/storage/shared/Music/EchoVault

echo "[4/6] Creating EchoVault directories..."

mkdir -p ~/EchoVault

echo ""
echo "Copy your EchoVault project into:"
echo ""
echo "~/EchoVault"
echo ""
echo "or"
echo ""
echo "~/storage/downloads"
echo ""

echo "[5/6] Detecting IP address..."

IP=$(ip route get 8.8.8.8 | awk '{print $7; exit}')

echo ""
echo "Android IP:"
echo "$IP"
echo ""

cat << EOF

=======================================
ACCESS FROM IPHONE USING:

http://$IP:5000

=======================================

IMPORTANT:

Modify app.py:

app.run(
    host="0.0.0.0",
    port=5000,
    debug=False
)

=======================================

EOF

echo "[6/6] Installer completed."
