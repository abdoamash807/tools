#!/bin/bash

echo "🔧 Updating system packages..."
sudo apt update

echo "📦 Installing required system tools..."
sudo apt install -y python3 python3-pip aria2 ffmpeg libffi-dev libssl-dev build-essential python3-libtorrent

echo "🐍 Installing Python packages..."
pip3 install --upgrade pip
pip3 install subliminal babelfish

echo "✅ All dependencies installed!"
echo "🎬 aria2c version: $(aria2c --version | head -n 1)"
echo "🎞️  ffmpeg version: $(ffmpeg -version | head -n 1)"
echo "🧲 libtorrent version: $(python3 -c 'import libtorrent as lt; print(lt.version)' 2>/dev/null || echo "libtorrent not found")"