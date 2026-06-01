#!/bin/zsh
set -euo pipefail

PROJECT_DIR="/Users/kaori/Documents/Codex/2026-05-21/fintech-lark-kol-substack-fintech-neobank"
LABEL="com.infini.fintech-radar"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$PROJECT_DIR/logs"

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>

  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>-lc</string>
    <string>cd "$PROJECT_DIR" &amp;&amp; PYTHONPYCACHEPREFIX=/private/tmp/python-cache /usr/bin/python3 -m fintech_radar --once --lookback-days 1 --timeout 8</string>
  </array>

  <key>StartCalendarInterval</key>
  <array>
    <dict>
      <key>Hour</key>
      <integer>9</integer>
      <key>Minute</key>
      <integer>0</integer>
    </dict>
    <dict>
      <key>Hour</key>
      <integer>18</integer>
      <key>Minute</key>
      <integer>0</integer>
    </dict>
  </array>

  <key>WorkingDirectory</key>
  <string>$PROJECT_DIR</string>

  <key>StandardOutPath</key>
  <string>$LOG_DIR/launchd.out.log</string>

  <key>StandardErrorPath</key>
  <string>$LOG_DIR/launchd.err.log</string>
</dict>
</plist>
PLIST

launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl enable "gui/$(id -u)/$LABEL"

echo "Installed $LABEL"
echo "Schedule: daily at 09:00 and 18:00 local time"
echo "Logs:"
echo "  $LOG_DIR/launchd.out.log"
echo "  $LOG_DIR/launchd.err.log"
