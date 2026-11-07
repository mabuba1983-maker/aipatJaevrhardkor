#!/data/data/com.termux/files/usr/bin/sh
# Run Nuwaa on the phone itself (Termux). CPU only, no GPU, no PyTorch.
set -e
pkg update -y && pkg install -y python python-numpy
export NUWAA_ADMIN_TOKEN="${NUWAA_ADMIN_TOKEN:-change-me-please}"
echo "open http://127.0.0.1:8000 in the phone browser. admin token: $NUWAA_ADMIN_TOKEN"
exec python server/server.py
