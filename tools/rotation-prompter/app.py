"""
RS3 Rotation Prompter -- tick-metronome overlay with an optional
autopress mode.

Two modes:
  - Prompt mode (default): shows/beeps the next ability to press. Sends
    nothing anywhere.
  - Autopress mode (F8, off by default): sends the mapped hotkey
    (rotations.py -> STYLES[style]["keys"]) to whatever window currently
    has focus, on the same cue. Make sure that's your game window, and
    that the key map actually matches your in-game action bar before you
    rely on it.

Autopress sends real keystrokes system-wide -- to whatever has focus,
not RS3 specifically. If Jagex's live servers are ever in the picture,
this is macroing under their rules and risks that account; this exists
for a self-hosted/private server where that's not a factor.

Controls (global hotkeys -- work even while the game has focus):
  F8   Toggle autopress mode on/off (off = prompt-only)
  F9   Start / pause the tick metronome
  F10  Reset to the start of the opener
  F11  Cycle style (Necromancy -> Magic -> Ranged -> Melee)
  F12  Toggle the audio cue on/off

If hotkeys (or autopress) don't reach the game window, try running this
from an Administrator terminal -- Windows blocks a low-privilege process
from hooking/sending keys over an elevated window, and games sometimes
launch elevated.
"""

import json
import os
import sys
import tkinter as tk

try:
    import keyboard  # global hotkeys
except ImportError:
    print("Missing dependency. Run: pip install -r requirements.txt")
    sys.exit(1)

try:
    import winsound
    def beep():
        winsound.Beep(880, 90)
except ImportError:
    def beep():
        pass  # non-Windows dev fallback; no audio cue

from rotations import STYLES, STYLE_ORDER

TICK_MS = 600  # 1 RS3 game tick

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
# Your personal key bindings, kept out of git (see keys.example.json) so
# `update.ps1` pulling the latest rotations.py never conflicts with them.
KEYS_CONFIG_PATH = os.path.join(TOOL_DIR, "keys.json")


def load_key_overrides():
    if os.path.exists(KEYS_CONFIG_PATH):
        with open(KEYS_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


class Prompter:
    def __init__(self, root):
        self.root = root
        self.style_idx = 0
        self.running = False
        self.sound_on = True
        self.autopress = False
        self.key_overrides = load_key_overrides()
        self.tick = 0
        self.step_idx = -1  # -1 = not started
        self.in_loop = False
        self.loop_pos = 0
        self.next_due_tick = 0

        self._build_window()
        self._bind_hotkeys()
        self._load_style()
        self._tick_loop()

    # ---------- UI ----------

    def _build_window(self):
        r = self.root
        r.title("RS3 Rotation Prompter")
        r.overrideredirect(True)
        r.attributes("-topmost", True)
        try:
            r.attributes("-alpha", 0.92)
        except tk.TclError:
            pass
        r.geometry("360x170+40+40")
        r.configure(bg="#141219")

        self.accent = tk.Frame(r, height=5, bg="#a780f2")
        self.accent.pack(fill="x", side="top")

        body = tk.Frame(r, bg="#141219")
        body.pack(fill="both", expand=True, padx=14, pady=(8, 12))

        self.style_label = tk.Label(
            body, text="NECROMANCY", fg="#a39dbb", bg="#141219",
            font=("Segoe UI", 9, "bold"))
        self.style_label.pack(anchor="w")

        self.now_label = tk.Label(
            body, text="Press F9 to start", fg="#ece9f5", bg="#141219",
            font=("Segoe UI", 20, "bold"), wraplength=330, justify="left")
        self.now_label.pack(anchor="w", pady=(4, 2))

        self.next_label = tk.Label(
            body, text="", fg="#a39dbb", bg="#141219",
            font=("Segoe UI", 11), wraplength=330, justify="left")
        self.next_label.pack(anchor="w")

        self.tick_label = tk.Label(
            body, text="tick 0", fg="#5c5968", bg="#141219",
            font=("Consolas", 9))
        self.tick_label.pack(anchor="w", pady=(8, 0))

        self.mode_label = tk.Label(
            body, text="PROMPT ONLY", fg="#5c5968", bg="#141219",
            font=("Segoe UI", 8, "bold"))
        self.mode_label.pack(anchor="w", side="bottom", pady=(0, 2))

        self.hint_label = tk.Label(
            body,
            text="F8 autopress  F9 start/pause  F10 reset  F11 style  F12 sound",
            fg="#5c5968", bg="#141219", font=("Consolas", 8))
        self.hint_label.pack(anchor="w", side="bottom")

        # Drag window by clicking anywhere on it
        for widget in (r, body, self.now_label, self.style_label):
            widget.bind("<ButtonPress-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._do_drag)

    def _start_drag(self, event):
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()

    def _do_drag(self, event):
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    # ---------- hotkeys ----------

    def _bind_hotkeys(self):
        keyboard.add_hotkey("f8", self._toggle_autopress)
        keyboard.add_hotkey("f9", self._toggle_running)
        keyboard.add_hotkey("f10", self._reset)
        keyboard.add_hotkey("f11", self._cycle_style)
        keyboard.add_hotkey("f12", self._toggle_sound)

    def _toggle_autopress(self):
        self.autopress = not self.autopress
        if self.autopress:
            self.mode_label.configure(text="AUTOPRESS ARMED", fg="#ff7a70")
        else:
            self.mode_label.configure(text="PROMPT ONLY", fg="#5c5968")

    def _toggle_running(self):
        self.running = not self.running
        if self.running and self.step_idx == -1:
            self._reset(keep_running=True)

    def _reset(self, keep_running=False):
        self.tick = 0
        self.step_idx = 0
        self.in_loop = False
        self.loop_pos = 0
        if not keep_running:
            self.running = False
        opener = self.style["opener"]
        self.next_due_tick = opener[0][1]
        self._render_current(opener[0][0])

    def _cycle_style(self):
        self.style_idx = (self.style_idx + 1) % len(STYLE_ORDER)
        self._load_style()
        self._reset()

    def _toggle_sound(self):
        self.sound_on = not self.sound_on

    def _load_style(self):
        key = STYLE_ORDER[self.style_idx]
        self.style = STYLES[key]
        self.active_keys = {
            **self.style["keys"],
            **self.key_overrides.get(key, {}),
        }
        self.accent.configure(bg=self.style["color"])
        self.style_label.configure(
            text=self.style["label"].upper(), fg=self.style["color"])
        self._reset()

    # ---------- tick engine ----------

    def _tick_loop(self):
        if self.running:
            self.tick += 1
            self.tick_label.configure(text=f"tick {self.tick}")
            self._maybe_advance()
        self.root.after(TICK_MS, self._tick_loop)

    def _maybe_advance(self):
        if self.tick < self.next_due_tick:
            return

        opener = self.style["opener"]
        loop = self.style["loop"]
        interval = self.style["loop_interval_ticks"]

        if not self.in_loop:
            self.step_idx += 1
            if self.step_idx >= len(opener):
                self.in_loop = True
                self.loop_pos = 0
                self.next_due_tick = self.tick + interval
                self._render_current(loop[0])
                self._cue()
                return
            name, _ = opener[self.step_idx]
            self._render_current(name)
            if self.step_idx + 1 < len(opener):
                self.next_due_tick = self.tick + opener[self.step_idx + 1][1]
            else:
                self.next_due_tick = self.tick + interval
            self._cue()
        else:
            self.loop_pos = (self.loop_pos + 1) % len(loop)
            self.next_due_tick = self.tick + interval
            self._render_current(loop[self.loop_pos])
            self._cue()

    def _render_current(self, name):
        self.current_name = name
        self.now_label.configure(text=name)
        upcoming = self._peek_next(name)
        self.next_label.configure(text=f"next: {upcoming}" if upcoming else "")

    def _peek_next(self, current_name):
        opener = self.style["opener"]
        loop = self.style["loop"]
        if not self.in_loop:
            nxt_idx = self.step_idx + 1
            if nxt_idx < len(opener):
                return opener[nxt_idx][0]
            return loop[0]
        return loop[(self.loop_pos + 1) % len(loop)]

    def _cue(self):
        if self.sound_on:
            beep()
        if self.autopress:
            key = self.active_keys.get(self.current_name)
            if key:
                keyboard.send(key)


def main():
    root = tk.Tk()
    Prompter(root)
    root.mainloop()


if __name__ == "__main__":
    main()
