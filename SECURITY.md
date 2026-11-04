# Security

## Installing this plugin runs its code

That is true of every plugin, and marketplace plugin-injection is a documented attack, so it
is worth stating plainly rather than assuming.

Read these before installing:

| Path | What it does |
|---|---|
| `scripts/setup.sh` | installs npm deps and downloads a Chromium binary (~100MB) |
| `scripts/*.py`, `scripts/*.cjs` | render cards, run Playwright, invoke `ffmpeg` |
| `scripts/calibrate.py` | spawns `claude -p` subprocesses to score fixtures |
| `scripts/handoff.sh` | writes files and starts a local HTTP server on request |
| `.github/workflows/ci.yml` | runs the above in CI |

## What it does not do

- No MCP servers, so it adds nothing to your tool budget and opens no server surface.
- No network calls except: npm install, the Chromium download, and Google Fonts at render time.
  A brand using `font.source: "local"` removes the last one.
- Nothing is published, posted, or uploaded. The pipeline stops at a file on disk.
- No credentials are read or written.

## Reporting

Open a private security advisory on the repository.
