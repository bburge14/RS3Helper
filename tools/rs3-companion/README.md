# RS3 Companion

One app: pick a style, a boss, and a Revo mode to see the tuned bar,
mechanics, and gear notes; practice the manual thresholds/ultimates
against a tick metronome with optional autopress; manage key bindings
and updates — all from the same window. Replaces the old standalone
`rotation-prompter` overlay script.

## Setup (Windows)

From this folder in PowerShell:

```
powershell -ExecutionPolicy Bypass -File install.ps1
```

This finds Python, creates an isolated `.venv` here, installs
`requirements.txt` (CustomTkinter + the `keyboard` global-hotkey
library) into it, and drops a desktop shortcut that launches the app
silently (no console window).

If Windows blocks the script outright: right-click `install.ps1` →
Properties → check **Unblock** → OK, then run the command above.

No installer, just want to run it directly:

```
pip install -r requirements.txt
python app.py
```

If hotkeys (or autopress) don't reach the game while it's focused, run
as **Administrator** — Windows blocks a low-privilege process from
hooking/sending keys over an elevated window, and games sometimes
launch elevated. Right-click the desktop shortcut → Run as
administrator.

## Closing the app

CustomTkinter windows occasionally render with no OS title bar on
Windows (a known upstream quirk). The app works around it on launch, but
if you ever end up with a window you can't find a title bar or × on:
Alt+F4 with it focused, or Ctrl+Shift+Esc → Task Manager → end
`python.exe`/`pythonw.exe`. Every pop-out window also closes on Escape
regardless of title bar state.

## Layout

Practice is the main window — it's what you actually watch during a
kill, so it's what opens. Style / Boss / Mode selectors sit in a bar
across the top, and two buttons open the rest as separate pop-out
windows you can leave closed while playing:

- **Bar Builder** — the full ordered bar (ability, type, and its role
  under whichever mode you picked), boss-specific mechanics and bar
  adjustments when a boss is selected, the style's defensive/utility
  matrix, and gear/relic tuning. Reference material — check it before a
  kill, not something you need open during one.
- **Settings** — key bindings and the updater (see below).

Changing Style / Boss / Mode on the main window updates the Bar Builder
pop-out live if it's open.

**Practice** — the tick metronome. Press Start the instant your first
hit lands (that's tick 0), and it cues the manual threshold/ultimate
sequence from there. A Guitar Hero-style lane shows upcoming abilities
scrolling in from the right toward a hit-line, flashing when each one's
due — so you can see the actual timing, not just read a label change.
Two modes, both drive the same lane:
- **Prompt mode** (default): shows/beeps the next ability. Sends
  nothing anywhere.
- **Autopress** (F8 or the switch, off by default): also sends the
  bound key on the same cue, to whichever window currently has focus.

Autopress is system-wide keystroke injection, not scoped to one game
window. This is built for a self-hosted/private server, not Jagex's
live game — on the live game, a program that presses ability hotkeys
for you is macroing under Jagex's rules regardless of who designed the
rotation, and risks the account being banned. That risk doesn't apply
to your own server, but it's real if this ever points at a live
account.

"Pop-out overlay" opens a small always-on-top window mirroring the
current cue, for when you don't want the full app on top of the game.

**Settings** — edit key bindings per style (saved to your user config
folder, not the repo, so `git pull`/the updater never touches them),
and check/apply updates.

| Key | Action |
|-----|--------|
| F8  | Toggle autopress (off = prompt-only) |
| F9  | Start / pause the metronome |
| F10 | Reset to the opener |
| F11 | Cycle style |
| F12 | Toggle the audio cue |

All five also have buttons/switches on the Practice page if you'd
rather click than remember function keys.

## Updating

Automatic: a few seconds after launch, the app checks the latest GitHub
release in the background and, if it's newer, applies it right then —
a `git pull` if you cloned the repo, or a download-and-overwrite of its
own files if you installed from a zip. Either way it only touches files
on disk; the running app keeps executing what it already loaded, so a
green banner appears at the top — **"Update vX ready — restart to
apply"** — with a **Restart now** button that saves your config, closes,
and relaunches. Dismissing the banner doesn't undo the update; it's
already on disk and takes effect whenever you next restart normally.

If your repo checkout has local changes, the automatic git-pull path
skips itself rather than risk them — use Settings → Updates → **Check
for updates** to see why, and resolve them before it'll proceed.

Manual: Settings → Updates → **Check for updates** any time, then
**Update now**. Same underlying logic as the automatic check, just
triggered on demand. **Open releases page** is always there too, for a
plain manual download.

### Private repo + auto-update

If the repo is private, the updater's plain GitHub API calls can't see
it — you'll need a token:

1. On GitHub: Settings → Developer settings → **Personal access tokens**
   → **Fine-grained tokens** → Generate new token.
2. Repository access: **only select repositories** → this repo.
3. Permissions: **Contents: Read-only**. Nothing else.
4. Copy the generated token.
5. In this folder, create a file named `.github_token` (no extension)
   containing just the token, nothing else.

That file is gitignored — it never gets committed, never travels with
updates. Delete it any time to revoke local access (and revoke the
token on GitHub too, to actually kill it).

## Ability icons

Real RS3 ability icons are Jagex's copyrighted game art, so none are
bundled with this repo. By default every ability shows a generated
placeholder badge instead (a colored circle with its initials,
color-coded the same as the type tags). If you want the real icons,
drop your own PNGs (screenshotted from your own client) into
`icons/`, named to match the ability exactly — see `icons/README.md`.
That folder is gitignored, so your icons stay local and never get
pushed or bundled into a release zip.

## Data & accuracy

Ability names/priorities in `data.py` reflect the live-game kit at time
of writing and shift with Jagex balance passes — cross-check against
in-game tooltips before a serious kill. Boss `mechanics` entries are
deliberately high-level starter notes for the initial boss set (Telos,
Arch-Glacor, Solak, Nex: Angel of Death, Rasial, Vorago, Zamorak), not a
full mechanic-by-mechanic guide. Ask for a specific boss to be fleshed
out further, or a new one added, and that entry gets refined/added.

## Config location

Key bindings and preferences live in:
- Windows: `%APPDATA%\RS3Companion\config.json`
- macOS/Linux: `~/.config/RS3Companion/config.json`

Delete that file to reset everything to defaults.
