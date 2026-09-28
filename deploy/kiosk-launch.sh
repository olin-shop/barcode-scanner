#!/usr/bin/env bash
# Starts the barcode kiosk app and restarts it whenever it exits.
#
# Meant to run from the desktop session (XDG autostart, see install-autostart.sh) so
# DISPLAY / WAYLAND_DISPLAY are already set for the GUI.
#
# Log:            ~/.local/state/barcode-kiosk/kiosk.log (rotated at 5 MB)
# Stop restarts:  touch ~/.local/state/barcode-kiosk/stop   (then close the app)
# Resume:         rm ~/.local/state/barcode-kiosk/stop       (and run this script, or log in again)

set -u

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/barcode-kiosk"
LOG_FILE="$STATE_DIR/kiosk.log"
STOP_FILE="$STATE_DIR/stop"
POETRY="${POETRY:-$HOME/.local/bin/poetry}"
RESTART_DELAY="${RESTART_DELAY:-5}"  # seconds before the first restart
MAX_LOG_BYTES=$((5 * 1024 * 1024))

mkdir -p "$STATE_DIR"
cd "$REPO_DIR" || exit 1

log() {
    echo "$(date -Is) [launcher] $*" >>"$LOG_FILE"
}

rotate_log() {
    if [ -f "$LOG_FILE" ] && [ "$(stat -c %s "$LOG_FILE")" -gt "$MAX_LOG_BYTES" ]; then
        mv -f "$LOG_FILE" "$LOG_FILE.1"
    fi
}

# Only one launcher at a time; the lock is held for as long as this script runs.
exec 9>"$STATE_DIR/launcher.lock"
if ! flock -n 9; then
    log "another launcher is already running; exiting"
    exit 0
fi

PYTHON="$("$POETRY" env info --executable 2>/dev/null)"
if [ ! -x "$PYTHON" ]; then
    log "poetry environment not found (run 'poetry install' in $REPO_DIR); exiting"
    exit 1
fi

delay=$RESTART_DELAY
while true; do
    if [ -e "$STOP_FILE" ]; then
        log "stop file present ($STOP_FILE); not starting the app"
        exit 0
    fi

    rotate_log
    log "starting kiosk app"
    started=$(date +%s)
    "$PYTHON" src/main.py >>"$LOG_FILE" 2>&1
    code=$?
    log "kiosk app exited with code $code"

    # Restart quickly after a long healthy run; back off (up to 60 s) if it keeps crashing.
    if [ $(($(date +%s) - started)) -gt 60 ]; then
        delay=$RESTART_DELAY
    elif [ "$delay" -lt 60 ]; then
        delay=$((delay * 2))
    fi
    sleep "$delay"
done
