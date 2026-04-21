#!/usr/bin/env bash
# One-time setup: trust Caddy's local CA in the Windows certificate store.
# Run after the first `docker compose up` from the repo root.
set -euo pipefail

CONTAINER_CERT="/data/caddy/pki/authorities/local/root.crt"
OUTPUT="./caddy-root.crt"

if ! docker compose ps caddy --status running -q 2>/dev/null | grep -q .; then
  echo "ERROR: caddy container is not running. Start the stack first: docker compose up -d"
  exit 1
fi

docker compose cp "caddy:${CONTAINER_CERT}" "$OUTPUT"
echo "Root cert exported to $OUTPUT"
echo ""

WIN_PATH=$(wslpath -w "$(realpath "$OUTPUT")" 2>/dev/null || echo "(convert path manually for Windows)")

echo "Trust it in Windows — pick one:"
echo ""
echo "  Option A — PowerShell (run as Administrator):"
echo "    certutil -addstore -f ROOT \"$WIN_PATH\""
echo ""
echo "  Option B — Explorer (no admin needed for current user):"
echo "    Double-click caddy-root.crt → Install Certificate"
echo "    → Current User → Trusted Root Certification Authorities"
echo ""
echo "Restart your browser after trusting. No more SSL warnings for https://localhost."
