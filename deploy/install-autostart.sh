#!/usr/bin/env bash
# Installs a desktop autostart entry so the kiosk app starts at login (and therefore
# after every reboot, since the Pi logs in automatically) via kiosk-launch.sh.
#
# Run once on the Pi as the kiosk user:  ./deploy/install-autostart.sh
# Remove with:                           rm ~/.config/autostart/barcode-kiosk.desktop

set -eu

LAUNCHER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/kiosk-launch.sh"
AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
ENTRY="$AUTOSTART_DIR/barcode-kiosk.desktop"

chmod +x "$LAUNCHER"
mkdir -p "$AUTOSTART_DIR"
cat >"$ENTRY" <<EOF
[Desktop Entry]
Type=Application
Name=Olin Shop Barcode Kiosk
Comment=Starts the barcode kiosk app and restarts it if it exits
Exec=$LAUNCHER
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

echo "Installed $ENTRY"
echo "It starts at the next login. To start it now instead, stop any hand-started copy"
echo "of the app first (only one can use port 5000), then run: $LAUNCHER &"
