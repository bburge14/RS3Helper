# RS3 Rotation Prompter

A small always-on-top overlay that cues the next manual ability, paced
by a tick metronome. It's built to sit alongside a "Revo Basics" bar
(see `../../guides/four-styles-one-bar.html`): basics fire on their own
via Revolution, so this only cues the threshold/ultimate presses
Revolution won't make for you.

## Two modes

- **Prompt mode** (default): shows/beeps the next ability. Sends nothing
  anywhere — the only input it reads is its own control hotkeys.
- **Autopress mode** (F8, off by default): on the same cue, also sends
  the mapped hotkey from `rotations.py` (`STYLES[style]["keys"]`) to
  whichever window currently has focus.

Autopress is system-wide keystroke injection, not something scoped to
one game window — whatever has focus receives the key. Edit `keys.json`
(see below) to match your actual action-bar bindings before trusting it;
a stale mapping presses the wrong ability. This is built for a
self-hosted/private server, not Jagex's live game — on the live game, a
program that presses ability hotkeys for you is macroing under Jagex's
rules regardless of who designed the rotation, and risks the account
being banned. That risk doesn't apply to your own server, but it's real
if this ever points at a live account.

## Setup (Windows)

From this folder in PowerShell:

```
powershell -ExecutionPolicy Bypass -File install.ps1
```

This finds Python, creates an isolated `.venv` here, installs
`requirements.txt` into it, copies `keys.example.json` to `keys.json`
(your personal, gitignored bindings), and drops a desktop shortcut that
launches the overlay silently (no console window).

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

## Updating

```
powershell -ExecutionPolicy Bypass -File update.ps1
```

Pulls the latest commits (fast-forward only — it won't touch or discard
any local changes you've made) and refreshes dependencies. Your
`keys.json` is gitignored, so pulling never overwrites your bindings; if
an update adds abilities your `keys.json` doesn't have yet, the script
lists them so you can add bindings for the new ones.

## Using it

1. Launch the app, drag it wherever's out of your way.
2. Press **F11** until it shows the style you're using.
3. Start the kill. The instant your first hit lands, press **F9** — that's
   your tick-0 sync point.
4. Follow the prompts. The tick counter is a fixed 0.6s/tick metronome
   from that sync point; it does not re-sync itself, so if you get out
   of sync (lag, a stun, a phase transition), press **F9** to pause and
   **F10** to reset, then re-sync on your next hit.

| Key | Action |
|-----|--------|
| F8  | Toggle autopress mode (off = prompt-only) |
| F9  | Start / pause the metronome |
| F10 | Reset to the start of the opener |
| F11 | Cycle style (Necromancy → Magic → Ranged → Melee) |
| F12 | Toggle the audio cue |

The overlay shows **PROMPT ONLY** or **AUTOPRESS ARMED** at the bottom
so it's always visible which mode you're in.

## Key bindings (`keys.json`)

`keys.example.json` is the tracked template; `install.ps1` copies it to
`keys.json` on first run. Edit `keys.json` (not the example) to match
your real action bar — it's gitignored, so it survives `update.ps1`
pulling new rotation data. If you're not using the installer, copy it
yourself:

```
cp keys.example.json keys.json
```

## Tuning the cadence

The prompt timings in `rotations.py` are approximations meant to build
muscle memory, not a read of your actual adrenaline bar — the tool has
no way to know your real adrenaline (that would require reading the
game, which is the automation-adjacent line described above). If the
default cadence fires faster or slower than your thresholds actually
become available, adjust `loop_interval_ticks` per style in
`rotations.py` to match your own adrenaline generation speed.
