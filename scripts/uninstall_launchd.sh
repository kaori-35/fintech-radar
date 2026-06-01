#!/bin/zsh
set -euo pipefail

LABEL="com.infini.fintech-radar"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
rm -f "$PLIST"

echo "Uninstalled $LABEL"
