#!/usr/bin/env bash
# One-time setup: trust Caddy's local CA in the Windows certificate store.
# Run after the first `docker compose up` from the repo root.
set -euo pipefail

CERT="./caddy-data/caddy/pki/authorities/local/root.crt"

if [ ! -f "$CERT" ]; then
  echo "ERROR: $CERT not found. Start the stack first: docker compose up -d"
  exit 1
fi

cp "$CERT" ./caddy-root.crt
echo "Root cert exported to ./caddy-root.crt"
echo ""

WIN_PATH=$(wslpath -w "$(realpath ./caddy-root.crt)" 2>/dev/null || echo "(wslpath not available)")

echo "Trust it in Windows — pick one:"
echo ""
echo "  Option A — PowerShell (run as Administrator):"
echo "    certutil -addstore -f ROOT \"$WIN_PATH\""
echo ""
echo "  Option B — Explorer (no admin needed for current user):"
echo "    Double-click caddy-root.crt → Install Certificate"
echo "    → Current User → Trusted Root Certification Authorities"
echo ""
echo "Restart your browser after trusting. Done — no more SSL warnings for https://localhost."
