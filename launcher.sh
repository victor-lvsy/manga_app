#!/bin/bash
mount /dev/sda2 /media/victor/DD_RPI -o uid=1000,gid=1000


sudo -u victor -i bash << 'EOF'
export PATH="$PATH:/home/victor/.local/bin"
export PATH="$PATH:/home/victor/Documents/manga_app/.venv/bin"
cd /home/victor/Documents/manga_app
docker compose up
EOF