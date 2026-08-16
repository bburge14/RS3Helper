"""
RS3 Rotation Prompter -- a display-only overlay + tick metronome.

What this does:
  - Shows the next manual ability to press, based on the rotations in
    rotations.py, advanced by a tick counter you start yourself.
  - Optionally beeps on each cue.

What this deliberately does NOT do:
  - Send any keystrokes or clicks to RuneScape, or any other window.
  - Read RuneScape's memory, pixels, or process in any way.
It only listens for its OWN control hotkeys (start/stop/reset/switch
style) and draws a small always-on-top window. That distinction matters:
software that presses game hotkeys for you is macroing under Jagex's
rules and risks a ban, even when it's just replaying a rotation like
this one. This tool leaves every game input to you.

Controls (global hotkeys -- work even while RS3 has focus):
  F9   Start / pause the tick metronome
  F10  Reset to the start of the opener
  F11  Cycle style (Necromancy -> Magic -> Ranged -> Melee)
  F12  Toggle the audio cue on/off

If hotkeys don't respond while RS3 is focused, try running this from an
Administrator terminal -- Windows blocks low-privilege processes from
hooking keys over an elevated window, and RS3 sometimes runs elevated.
"""

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


class Prompter:
    def __init__(self, root):
        self.root = root
        self.style_idx = 0
        self.running = False
        self.sound_on = True
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

        self.hint_label = tk.Label(
            body, text="F9 start/pause  F10 reset  F11 style  F12 sound",
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
        keyboard.add_hotkey("f9", self._toggle_running)
        keyboard.add_hotkey("f10", self._reset)
        keyboard.add_hotkey("f11", self._cycle_style)
        keyboard.add_hotkey("f12", self._toggle_sound)

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


def main():
    root = tk.Tk()
    Prompter(root)
    root.mainloop()


if __name__ == "__main__":
    main()
