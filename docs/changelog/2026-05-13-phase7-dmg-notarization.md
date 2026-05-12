# Phase 7 — Signed/notarized .dmg and auto-update (13 May 2026)

`electron-builder` produces signed `.dmg` for arm64 and x64; `notarytool`
notarizes via `electron/notarize.js`. The PyInstaller sidecar is signed
separately (`scripts/sign-sidecar.sh`) with the same hardened-runtime
entitlements (`electron/entitlements.mac.plist`). `electron-updater` polls
`AUTO_UPDATE_FEED_URL`; renderer receives status events via the `updater`
preload bridge and shows a Header badge.

Required env (build-time): `APPLE_ID`, `APPLE_ID_PASSWORD` (app-specific),
`APPLE_TEAM_ID`, `APPLE_SIGNING_IDENTITY`, `CSC_LINK`, `CSC_KEY_PASSWORD`,
`AUTO_UPDATE_FEED_URL`. Set `SKIP_NOTARIZE=true` to bypass `notarize.js`
and `sign-sidecar.sh` for unsigned local development builds.

## Files
- `electron/package.json` — `afterSign`, `hardenedRuntime`, entitlements,
  dmg+zip targets for `arm64`/`x64`, `publish.generic`, `directories.output=../release`.
  Adds `electron-updater@^6.3.9` and `@electron/notarize@^2.5.0`.
- `electron/entitlements.mac.plist` — JIT, library-validation disabled,
  network client/server, dyld env vars.
- `electron/notarize.js` — afterSign hook (skipped when `SKIP_NOTARIZE=true`).
- `electron/updater.ts` (new) — wires `autoUpdater` events to renderer.
- `electron/main.ts` — calls `registerAutoUpdater(mainWindow)`.
- `electron/preload.ts` — exposes `window.updater.onStatus`.
- `scripts/sign-sidecar.sh` (new) — `codesign --options runtime` with the
  entitlements plist; honors `SKIP_NOTARIZE=true`.
- `scripts/build.sh` — invokes `sign-sidecar.sh` between PyInstaller and
  electron-builder.
- `app/config.py` + `.env.example` — `AUTO_UPDATE_FEED_URL` (informational; Electron reads `process.env`).
- `.github/workflows/release-mac.yml` (new) — gated `if: false` until
  `MAC_CERTS`/`MAC_CERTS_PASSWORD` and Apple secrets are stored.
- `frontend/src/components/layout/Header.tsx` — small badge showing
  update-available / download-progress / error.

## Manual verification (still owed)
Phase 7 plan Task 7.7 requires actually building, signing, and notarizing
the bundle. That step needs the engineer's Apple Developer cert in the
login keychain, `APPLE_*` env vars, and a network round-trip to Apple's
notarization service — it was **not** executed in this session.

Once the engineer has the prerequisites set up:

```bash
export APPLE_ID="you@example.com"
export APPLE_ID_PASSWORD="abcd-efgh-ijkl-mnop"   # app-specific
export APPLE_TEAM_ID="ABCDE12345"
export APPLE_SIGNING_IDENTITY="Developer ID Application: You (ABCDE12345)"
export AUTO_UPDATE_FEED_URL="https://updates.example.com/n8nrep/"
bash scripts/build.sh
xcrun stapler validate release/n8nrep-1.0.0-arm64.dmg
spctl --assess --type install -v release/n8nrep-1.0.0-arm64.dmg
```

Expected: `stapler` prints “The validate action worked!” and `spctl`
prints `accepted`. The first install will then auto-poll the feed URL on
launch; a published `1.0.1` should trigger the Header badge within 30s.
