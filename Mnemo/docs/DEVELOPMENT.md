# Mnemos (macOS & iPadOS)

Pip lives in your menu bar. Drop a technical book (PDF or EPUB) on Mnemos and every chapter becomes a structured 5-stage mastery loop: **Prime** (architectural briefing & dialogue), **Conversational Active Read** (in-situ developer co-pilot with *"Show Me in Code"* and *"Production Reality Check"*), **Socratic Recall** (verbal/conceptual explanation check), **Interactive Harness** (isolated verification sandbox with virtual clock/storage/network shims), and **Remember** (FSRS-4.5 spaced repetition).

65% of the core foundation is already built and operational in `apple/Sources/NeuralLoopCore` and `pipeline/`.

## Install

Download `Mnemos-<version>.dmg`, drag Mnemos to Applications, and open it. It isn't signed by Apple yet, so the first time macOS asks: open System Settings → Privacy & Security and choose **Open Anyway**. The lightweight runtime components it needs are self-contained inside the app bundle (Python 3.11+, provider connectors, and local model runner like Ollama).

After an update, macOS may ask once whether Mnemos may use what it saved in your keychain. Enter your Mac's login password and click **Always Allow**; that's Mnemos reading its API keys and sync credentials.

## Using it

- **Add a book**: drop it on the window or choose Add a book. Pip analyzes the chapters and generates chapter preparation ahead of your progress (<2s per chapter, fully textual and symbolic).
- **Settings** (⌘,): pick your AI provider and keys (kept in macOS Keychain), models (Claude, OpenAI, OpenRouter, local Ollama), and nudges (at most one a day, never in quiet hours, backing off if you skip them).
- **Menu bar**: pick up where you left off, review due cards, and launch interactive harness challenges.
- Books and progress live in `~/Library/Application Support/app.neuralloop.books/books/`.

## For developers

```bash
make setup     # once: Python dev tools and virtualenv
make check     # linters + every test (Python and Swift)
make mac       # build and open the app (Xcode + XcodeGen: brew install xcodegen)
make package   # dist/Mnemos-<version>.dmg
```

- `pipeline/` — Python 3.11+ processing engine (chapter split, prompt adapters, MCP gateway, DeepMind token optimizer).
- `apple/Sources/NeuralLoopCore` — Pure Swift domain logic (FSRS-4.5 math, loop state machine, telemetry, nudge policies).
- `apple/App` — Native SwiftUI views and macOS/iPadOS UI.
- `scripts/` — Packaging and release toolchain.

The core rules: pure logic lives in `NeuralLoopCore` and `pipeline/neuralloop_books`, backed by unit tests; UI screens stay thin. Full architectural contracts are documented in [docs/ARCHITECTURE.md](ARCHITECTURE.md) and [plan.md](../plan.md).

## Signing

`make package` makes an ad-hoc signed DMG for local distribution. Ollama and local CLI runtimes keep their own Developer ID signature.

Turning on hardened runtime for Apple Notarization requires:
- **Developer ID Application certificate** (Apple Developer Program) to sign with `--options runtime --timestamp`.
- **Entitlements for bundled runtime** (`apple/NeuralLoop.entitlements`).
- **Notarization** via `xcrun notarytool submit … --wait` and `xcrun stapler staple`.

## Google Drive sync

Your library follows you through a private folder in your Google Drive using the `drive.appdata` scope (only Mnemos can access this folder). There is no centralized server: clients synchronize directly to user-owned cloud storage.

1. Create a Google Cloud Project with the Google Drive API enabled.
2. Configure OAuth 2.0 Client ID for iOS/macOS (`app.neuralloop.books`).
3. Add the Client ID to `apple/Config/Google.xcconfig`.

## iPadOS Setup

For iPad deployment:
1. In Xcode: Sign in with your Apple ID under Settings → Accounts.
2. Set `NEURALLOOP_TEAM = <your Team ID>` in `apple/Config/Local.xcconfig`.
3. Enable Developer Mode on iPad (Settings → Privacy & Security → Developer Mode).
4. Select `NeuralLoopPad` scheme in Xcode and deploy via USB or Wi-Fi.
