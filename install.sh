#!/usr/bin/env bash
# install.sh — register codex-context-meter as the Codex CLI status line.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$SCRIPT_DIR/bin/codex-context-meter"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
CONFIG="$CODEX_HOME/config.toml"

chmod +x "$BIN"

mkdir -p "$CODEX_HOME"
touch "$CONFIG"

if grep -q '^\s*status_line' "$CONFIG"; then
    cp "$CONFIG" "$CONFIG.bak.$(date +%Y%m%d%H%M%S)"
    echo "⚠️  Existing status_line found in $CONFIG (backed up)."
    echo "    Replace it manually with:"
    echo "    status_line = [\"$BIN\"]"
    exit 0
fi

if grep -q '^\[tui\]' "$CONFIG"; then
    # Append inside the existing [tui] section: simplest reliable way is to
    # insert right after the [tui] header line.
    awk -v line="status_line = [\"$BIN\"]" '
        /^\[tui\]/ && !done { print; print line; done=1; next }
        { print }
    ' "$CONFIG" > "$CONFIG.tmp" && mv "$CONFIG.tmp" "$CONFIG"
else
    printf '\n[tui]\nstatus_line = ["%s"]\n' "$BIN" >> "$CONFIG"
fi

echo "✅ Installed. $CONFIG now contains:"
echo "   [tui]"
echo "   status_line = [\"$BIN\"]"
echo "Restart Codex to see the context meter below the input box."
echo "Detailed report anytime: $BIN report"
