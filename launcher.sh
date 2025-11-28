#!/bin/bash
mount /dev/sda2 /media/victor/DD_RPI -o uid=1000,gid=1000

# Wait until MySQL is ready
until mysqladmin ping -u root --silent; do
    echo "Waiting for MySQL…"
    sleep 2
done

echo "MySQL is up! Starting script..."

sudo -u victor -i bash << 'EOF'
export PATH="$PATH:/home/victor/.local/bin"
export PATH="$PATH:/home/victor/Documents/manga_app/.venv/bin"
cd /home/victor/Documents/manga_app
pipenv run python -m src.reader.app
EOF