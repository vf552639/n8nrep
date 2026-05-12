#!/usr/bin/env bash
# Sign the standalone PyInstaller sidecar with the Developer ID Application
# certificate and the same entitlements as the Electron app. Without this
# step, hardened-runtime + library-validation entitlement on the outer .app
# is not enough — embedded executables must each be signed.
set -euo pipefail

if [[ "${SKIP_NOTARIZE:-}" == "true" ]]; then
  echo "sign-sidecar: skipped (SKIP_NOTARIZE=true)"
  exit 0
fi

: "${APPLE_SIGNING_IDENTITY:?must be set, e.g., 'Developer ID Application: Name (TEAMID)'}"

SIDECAR="${1:-resources/sidecar}"
ENTITLEMENTS="electron/entitlements.mac.plist"

if [[ ! -f "$SIDECAR" ]]; then
  echo "sign-sidecar: $SIDECAR not found" >&2
  exit 1
fi

echo "sign-sidecar: signing $SIDECAR"
codesign --force --timestamp --options runtime \
  --entitlements "$ENTITLEMENTS" \
  --sign "$APPLE_SIGNING_IDENTITY" \
  "$SIDECAR"

echo "sign-sidecar: verifying"
codesign --verify --strict --verbose=4 "$SIDECAR"
echo "sign-sidecar: ok"
