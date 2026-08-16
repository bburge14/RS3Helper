# RS3 Rotation Prompter

A small always-on-top overlay that prompts you with the next manual
ability to press, paced by a tick metronome. It's built to sit alongside
a "Revo Basics" bar (see `../../guides/four-styles-one-bar.html`): basics
fire on their own via Revolution, so this only cues the threshold/
ultimate presses Revolution won't make for you.

## What it does and doesn't do

- Draws a small overlay window and beeps on cue. That's it.
- It does **not** send any keystrokes or clicks into RuneScape, and does
  **not** read RuneScape's memory, pixels, or process.
- The only input it reads is its own control hotkeys (start/pause/reset/
  switch style), so you can drive it without alt-tabbing.

This split matters: a program that presses game hotkeys for you is
macroing under Jagex's rules, even if a human designed the rotation, and
risks the account being banned. A program that just tells you what to
press, leaving the actual input to you, doesn't cross that line.

## Setup

```
pip install -r requirements.txt
python app.py
```

Requires Windows for the `keyboard` global-hotkey library to reliably
work over another focused window (RS3). It'll run on other platforms for
testing the UI, but global hotkeys and the beep are Windows-specific.

If hotkeys don't fire while RS3 is focused, run your terminal as
**Administrator** — Windows blocks a low-privilege process from hooking
keys over an elevated window, and RS3 sometimes launches elevated.

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
| F9  | Start / pause the metronome |
| F10 | Reset to the start of the opener |
| F11 | Cycle style (Necromancy → Magic → Ranged → Melee) |
| F12 | Toggle the audio cue |

## Tuning the cadence

The prompt timings in `rotations.py` are approximations meant to build
muscle memory, not a read of your actual adrenaline bar — the tool has
no way to know your real adrenaline (that would require reading the
game, which is the automation-adjacent line described above). If the
default cadence fires faster or slower than your thresholds actually
become available, adjust `loop_interval_ticks` per style in
`rotations.py` to match your own adrenaline generation speed.
