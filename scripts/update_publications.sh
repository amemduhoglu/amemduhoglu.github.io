#!/usr/bin/env bash
# Monthly Google Scholar publication updater
# Cron: 0 3 1 * *  (her ayın 1'i, 03:00)

set -euo pipefail

REPO_DIR="/home/kadir/amemduhoglu.github.io"
VENV_PYTHON="/tmp/scholar-venv/bin/python"
LOG="$REPO_DIR/logs/publications_update.log"

mkdir -p "$REPO_DIR/logs"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG"; }

log "=== Güncelleme başladı ==="

# Venv yoksa oluştur
if [ ! -f "$VENV_PYTHON" ]; then
    log "venv bulunamadı, oluşturuluyor..."
    python3 -m venv /tmp/scholar-venv
    /tmp/scholar-venv/bin/pip install -q scholarly
    log "venv oluşturuldu"
fi

cd "$REPO_DIR"

# Fetch publications
log "Google Scholar'dan çekiliyor..."
if $VENV_PYTHON fetch_publications.py >> "$LOG" 2>&1; then
    log "Çekme başarılı"
else
    log "HATA: fetch_publications.py başarısız"
    exit 1
fi

# Değişiklik varsa commit + push
if git diff --quiet assets/data/publications.json 2>/dev/null; then
    log "Değişiklik yok, push atlanıyor"
else
    git add assets/data/publications.json
    git commit -m "chore: auto-update publications from Google Scholar"
    git push origin main >> "$LOG" 2>&1
    log "Push başarılı"
fi

log "=== Güncelleme tamamlandı ==="
